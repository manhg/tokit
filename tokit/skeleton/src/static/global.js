window.onerror = function(message, url, line) {
  if (line == 0) return false;
  // TODO Log exception to backend
  // location.pathname + ' @ ' + url + ':' + line + ' ' + message
  // (Array.prototype.slice.call(arguments));
  return true;
};

(function(riot) {
  if (!!riot) return;

  //
  // Flux-like controller
  //
  riot.ctrl = {
    _stores: [],
    addStore: function(store) {
      this._stores.push(store);
    },
    reset: function() {
      this._stores = [];
    }
  };
  ['on','one','off','trigger'].forEach(function(api) {
    riot.ctrl[api] = function() {
      var args = [].slice.call(arguments);
      this._stores.forEach(function(el){
        el[api].apply(el, args);
      });
    };
  });

  //
  // Mount a script tag into Riot tag.
  // Used when opts are complex
  //
  // Example:
  //    <script type="riot/inline" data-tag="x-greet">{"title": "Hello"}</script>
  //    <!-- will mounted as same as -->
  //    <x-greet title="Hello"></x-greet>
  //
  riot.inline = function(element) {
    var tags = element ? [element] :
      document.querySelectorAll('script[type=riot/inline]');
    var length = tags.length;
    for (var i = 0; i < length; i++) {
      riot.mount(
        document.createElement(element.getAttribute('data-tag')),
        JSON.parse(element.innerHTML) /* opts */
      );
      element.parentNode.insertBefore(root, element);
    }
  };
  
  // Mount
  riot.inline();

  // TODO find tags and autoload definitions, might be a filter from Python
  riot.mount('*');
})(riot);

