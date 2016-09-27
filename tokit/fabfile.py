import os
import random
import string

from fabric3.operations import local, put
from fabric3.context_managers import lcd, cd, hide
from fabric3.contrib.project import rsync_project
from fabric3.contrib.files import exists
from fabric3.decorators import runs_once
from fabric3.api import run, env, hosts
from fabric3.api import settings
from fabric3.colors import green, red
from tokit.utils import rand

# Skip using git, imply force deploy
SKIP_PREPARE = os.environ.get('SKIP_PREPARE', False)

# Force deploy: override existing deployments
FORCE_DEPLOY = os.environ.get('FORCE_DEPLOY', SKIP_PREPARE)

DEPLOY_BRANCH = os.environ.get('DEPLOY_BRANCH', 'origin/master')
DEPENDENT_FILE = 'requirements.txt'
RSYNC_EXCLUDES = [
    '/.git*', '/tmp', '.env', '/logs'
]
LINK_DIRS = []
LINK_FILES = []

current_dir = os.path.abspath(os.path.dirname(__file__))

stamp = rand(6)


# if Git is not clean, save stash and store current branch
if not SKIP_PREPARE:
    with hide('output', 'running'):
        dirty_branch = None
        is_dirty = local('git diff --shortstat 2> /dev/null | tail -n1', capture=True)
        if is_dirty:
            print(red("Having ongoing change code, will save it"))
            dirty_branch = local('git rev-parse --abbrev-ref HEAD', capture=True)

def get_version():
    if FORCE_DEPLOY:
        # force deploy by create a special version
        v = 'force_' + stamp
    else:
        v = local('git rev-parse --short %s' % DEPLOY_BRANCH, capture=True)
    return v

def remove_old_versions(path):
    keep_last = 5
    with cd(path):
        # remove old old
        run("ls -1tr | head -n -%d | xargs -d '\n' rm -Rf " % keep_last)

def check(dest_path):
    test_domain = os.environ.get('TEST_DOMAIN')
    if not test_domain:
        return

    with cd(dest_path):
        # query a test URL using new code to see if it works
        run('ln -sfn versions/%s test' % get_version())
        status = run(
            'curl -sL -w "%{http_code} %{url_effective}\\n" ' +
            '--header "Host: ' + test_domain + '" -o /dev/null ' +
            'http://127.0.0.1:80/'
        )
        if '200' not in status:
            raise RuntimeError('Domain test failed')

def deploy_to(dest_path):
    v = get_version()

    if not exists(dest_path + '/versions'):
        run('mkdir -p %s/versions' % dest_path)

    if not exists(dest_path + '/versions/' + v):
        rsync_project(
            dest_path + '/versions/tmp', current_dir + '/',
            exclude=RSYNC_EXCLUDES,
            extra_opts='--delete-after --links'
        )
        # links
        with cd(dest_path):
            run('cp -R versions/tmp versions/%s' % v)

    with cd(dest_path + '/versions/' + v):
        for d in LINK_DIRS:
            shared_d = '%s/shared/%s' % (dest_path, d)
            if not exists(shared_d):
                run('mkdir -p ' + shared_d)
                run('chmod 770 ' + shared_d)
            run('ln -sfn %s .' % (shared_d))

        for f in LINK_FILES:
            run("ln -sf {dest}/shared/{f} {f}".format(
                f=f, dest=dest_path
            ))


def finalize(dest_path):
    v = get_version()
    with cd(dest_path):
        run('ln -sfn versions/%s current' % v)
    remove_old_versions(dest_path + '/versions/')

def restore():
    if SKIP_PREPARE:
        return
    if dirty_branch:
        local('git checkout ' + dirty_branch)
        local('git stash apply')
    else:
        local('git checkout master')

def prepare(dest_path):
    if SKIP_PREPARE:
        return
    if dirty_branch:
        local('git stash')
    local('git fetch --all', capture=True)
    local('git checkout %s' % DEPLOY_BRANCH, capture=True)

    update_dependents = True
    if exists(dest_path + '/current'):
        current_path = run('readlink -f %s/current' % dest_path)
        current_hash = os.path.basename(current_path.strip())
        if current_hash == get_version():
            raise RuntimeError('Already deployed version ' + current_hash)
        if 'force_' not in current_hash:
            changes = local(
                'git diff --name-only origin/master ' + current_hash,
                capture=True
            )
            if not DEPENDENT_FILE in changes:
                update_dependents = False

    if update_dependents:
        run('pip install -r requirements.txt')

def deploy(srv_path):
    try:
        with hide('output', 'running'):
            prepare(srv_path)
            deploy_to(srv_path)
            check(srv_path)
            finalize(srv_path)
        print(green("Success"))
    except RuntimeError as e:
        print(red(e.message))
        restore()


@runs_once
def ask_version(ver, dest):
    with hide('output', 'running'):
        if not ver:
            current_path = run('readlink -f %s/current' % dest)
            current_hash = os.path.basename(current_path.strip())
            print("Current version", green(current_hash))
            versions = run('ls -t {dest}/versions'.format(dest=dest))
            versions = re.split('\s+', versions.replace('tmp', '').replace(current_path, ''))
            # first is often current version
            ver = versions[1]
        modified = run('stat --format="%y" {dest}/versions/{ver}'.format(dest=dest, ver=ver))
    from fabric.contrib.console import confirm
    print(red("[IMPORTANT]"))
    print("Detected last version: " + yellow(ver))
    print("All versions: ", ', '.join(versions))
    ok = confirm(yellow(
        "Do you want to revert to  " + ver + " version? Deployed at " + modified[0:16],
        default=False
    ))
    return ver if ok else False

def revert(dest_path, ver=None):
    ver = ask_version(ver, dest_path)
    if ver:
        run((
            'cd {dest_path}; '
            'if test -d versions/{v} ; then '
                'ln -sfn versions/{v} current ; '
            'fi'
        ).format(v=ver, dest_path=dest_path))
        print(green("Reverted into" + ver))
    else:
        print(red("Canceled"))


class _X:
    """ Custom variables """
    app = None
    base_port = 7000
    n_instances = 2
    remote_path = '/home/'
    wait = 3
    excludes = ('.*', 'tmp', '__pycache__', '*.pyc', 'upload', 'cache')
    dirs = ['config', 'src', 'doc']


env.x = _X()

def pwd(base_file):
    _pwd = os.path.dirname(base_file)
    os.chdir(_pwd)

def with_root():
    env.user = 'root'

@contextlib.contextmanager
def on_remote(path=''):
    with cd(os.path.join(env.x.remote_path, path)):
        yield


@contextlib.contextmanager
def venv(inside=''):
    with prefix('source {remote}/bin/activate' \
                        .format(remote=env.x.remote_path)), cd(env.x.remote_path + inside):
        yield

def sync(dirs=None):
    if dirs:
        dirs = dirs.split(',')
    else:
        dirs = env.x.dirs
    for d in dirs:
        fab_project.rsync_project(
            remote_dir=env.x.remote_path, local_dir=d,
            exclude=env.x.excludes,
            extra_opts='--delete-after'
        )


def backend(action='restart'):
    """ (3) Start services """
    with_root()
    systemd_reload()
    for instance in range(env.x.n_instances):
        run('systemctl {action} {app}@{port}.service'.format(
            action=action,
            app=env.x.app,
            port=env.x.base_port + instance))
        time.sleep(env.x.wait)


def config():
    """ (3) Link configs """
    with_root()
    with on_remote():
        for instance in range(env.x.n_instances):
            service_file = "/etc/systemd/system/multi-user.target.wants/{app}@{port}.service" \
                .format(app=env.x.app, port=env.x.base_port + instance)
            run("ln -s -f {path}/config/app@.service {dest}" \
                .format(path=env.x.remote_path, dest=service_file))
        run('ln -s -f {path}/config/nginx.conf /etc/nginx/conf.d/{app}.conf' \
            .format(app=env.x.app, path=env.x.remote_path))


def rollback():
    with on_remote():
        run('mv src src-fail && mv rollback src')
        backend('restart')


def ssh_setup(public_key='~/.ssh/id_rsa.pub'):
    """ (0) Create user, add SSH key, create folders """
    env.user = 'root'
    run('useradd %s' % env.x.app)
    run('mkdir -p /home/%s/{.ssh,tmp,shared,src,var}' % env.x.app)
    run('ssh-keygen -b 2048 -t rsa -f /home/%s/.ssh/id_rsa -q -N ""' % env.x.app)
    put(public_key, '/home/%s/.ssh/authorized_keys' % env.x.app)
    run('chown %s -R /home/%s' % (env.x.app, env.x.app))
    run('chmod 700 /home/%s' % env.x.app)


def authorize_key(key=None):
    """ Add an user to access server """
    if key:
        run('cat "%s">> /home/%s/.ssh/authorized_keys' % (key, env.x.app))
    else:
        print("Please provide a SSH public key")


def static_copy():
    with_root()
    run('mkdir -p /var/www/{app}'.format(app=env.x.app))
    run('cp -R {path}/src/static /var/www/{app}/'.format(path=env.x.remote_path, app=env.x.app))
    run('chown -R nginx /var/www/{app}/'.format(path=env.x.remote_path, app=env.x.app))


def systemd_reload():
    with_root()
    run('systemctl daemon-reload')


def up_file(name):
    os.path.dirname(name)
    rel = os.path.relpath(name, PWD)
    print(put(name, os.path.join(env.x.remote_path, rel)))


def up_python():
    with_root()
    backend('restart')


def up_nginx():
    # Pitfall
    with_root()
    config()
    systemd_reload()
    run('nginx -t && systemctl reload nginx.service')


def nginx(action='restart'):
    with_root()
    # PITFALL: first start must be a restart, not reload
    run('nginx -t && systemctl ' + action + ' nginx.service')


def find_files(directory, patterns):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            for pattern in patterns:
                if fnmatch.fnmatch(basename, pattern):
                    yield (root, basename)

def up_project():
    fab_project.rsync_project(
        remote_dir=env.x.remote_path, local_dir='src',
        upload=True, extra_opts='-a ', exclude=('__pycache__'))


def doc(browser=True):
    """ Generate and display document in browser"""
    with fab_context.lcd('doc'):
        local('make')
    if browser:
        with fab_context.lcd('doc'):
            local('cd _build/html && python3 -m http.server 7359 >/dev/null 2>&1 &')
            local('open http://localhost:7359/')


def pg_dump_schema(db=None):
    import getpass
    local_username = getpass.getuser()
    if not db:
        db = env.x.app
    local('pg_dump -s %s  > config/schema.sql' % db)
    local('sed -i s/{local}/{remote}/g config/schema.sql'.format(local=local_username, remote=env.x.app))


def pg_up_schema():
    with _Temp(delete=False, suffix='.dat') as tmp:
        local(
            ("pg_dump --schema-only "
            "--no-owner --no-acl --no-privileges "
            "--file={temp} {db} ")
            .format(temp=tmp.name, db=env.x.app))
        remote_sql = '{path}/tmp/schema.sql'.format(path=env.x.remote_path)
        put(tmp.name, remote_sql)
        run('psql {app} < {sql}'.format(sql=remote_sql, app=env.x.app))


def pg_up_data():
    with _Temp(delete=False, suffix='.dat') as tmp:
        local(
            ("pg_dump --data-only "
            "--no-owner --no-acl --no-privileges "
            "--file={temp} {db} ")
            .format(temp=tmp.name, db=env.x.app))
        remote_sql = '{path}/tmp/data.sql'.format(path=env.x.remote_path)
        put(tmp.name, remote_sql)
        run('psql {app} < {sql}'.format(sql=remote_sql, app=env.x.app))


def pg_setup():
    """
    Create random database and user with password on remote server
    and save credential into production.ini config file
    """
    passwd = rand()
    with open('config/production.ini', 'a') as f:
        lines = [
            '[postgres]',
            'dsn=user={app} dbname={app} password={passwd}'.format(app=env.x.app, passwd=passwd),
            'size=4'
        ]
        for line in lines:
            f.write(line + "\n")
    with_root()
    sql_file = '/tmp/' + rand() + '.sql'
    with _Temp(suffix='.sql') as tmp:
        with open(tmp.name, 'w') as f:
            sql = """
                CREATE USER {app} WITH PASSWORD '{passwd}';
                CREATE DATABASE {app} ENCODING='UTF8';
                GRANT ALL PRIVILEGES ON DATABASE {app} TO {app}
                """.format(passwd=passwd, app=env.x.app)
            f.write(sql)
            f.flush()
            put(tmp.name, sql_file)
    with on_remote('/tmp'):
        run("""su postgres -c 'cat {sql_file} | psql template1' """.format(sql_file=sql_file))
        run('rm ' + sql_file)


def static_link():
    """ Collect static files by symbolic links """
    original_dir = 'src'
    link_dir = 'public'
    for brick_path, basename in find_files(original_dir,[
        '*.css', '*.js', '*.tag'
        '*.png', '*.jpg', '*.gif', '*.json',
        '*.txt', '*.pdf',
    ]):
        static_path = brick_path.replace(original_dir, link_dir)
        if not os.path.exists(static_path):
            os.makedirs(static_path)
        # Make symlinks
        rel_path = os.path.relpath(original_dir, static_path)
        rel = os.path.join(brick_path.replace(original_dir, rel_path), basename)
        dst = os.path.join(static_path, basename)
        print(rel, dst)
        if not os.path.islink(dst):
            os.symlink(rel, dst)
    with fab_context.lcd(link_dir):
        # Remove all broken links
        local('find -xtype l -delete')
