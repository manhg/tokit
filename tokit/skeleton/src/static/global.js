window.onerror = function(message, url, line) {
  if (line !== 0) {
    // Log exception
    // location.pathname + ' @ ' + url + ':' + line + ' ' + message
    if ('console' in window) {
        console.log(Array.prototype.slice.call(arguments));
    }
  }
  return false;
};

(function() {
  function buildUX(element) {
    var tagname = element.getAttribute('tagname');
    var root = document.createElement(tagname);
    var opts = JSON.parse(element.innerHTML);
    riot.mount(root, tagname, opts);
    element.parentNode.insertBefore(root, element);
  }

  var tags = document.querySelectorAll('script[type=tag]');
  var length = tags.length;
  for (var i = 0; i < length; i++) {
    buildUX(tags[i]);
  }
})();
