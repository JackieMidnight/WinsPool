/*
 * Tiny runtime for the Philly Wins Pool pages.
 *
 * Each page holds its markup in <template id="dc-template"> and its logic in
 * <script type="text/x-dc" data-dc-script>. The logic class's renderVals()
 * returns the values the template reads through {{holes}}. Supported template
 * syntax: {{dotted.path}} in text and attributes, onClick="{{handler}}",
 * <sc-for list="{{items}}" as="item"> and <sc-if value="{{cond}}">.
 * An attribute written dc-name="..." is set as name="..." once filled in.
 *
 * The light/dark choice is remembered across pages in localStorage.
 *
 * On screens 1024px and wider, the phone-first pages switch to a desktop
 * layout: the menu moves into the header and the sections sit in a two-column
 * grid. A section's data-wide attribute places it: "left", "right", "full"
 * (both columns, the default) or "bleed" (edge to edge). data-pad keeps a
 * boxed section's own side padding; data-sticky pins a left column in place;
 * data-stack stacks its child sections in one column.
 */
(function () {
  var THEME_KEY = 'pwp-theme';

  function readTheme() {
    try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
  }
  function saveTheme(mode) {
    try { localStorage.setItem(THEME_KEY, mode); } catch (e) { /* storage blocked */ }
  }

  function DCLogic(props) {
    this.props = props || {};
    this.state = {};
  }
  DCLogic.prototype.setState = function (patch) {
    var next = typeof patch === 'function' ? patch(this.state, this.props) : patch;
    this.state = Object.assign({}, this.state, next);
    if (next && next.mode) {
      saveTheme(next.mode);
      this.props = Object.assign({}, this.props, { mode: next.mode });
    }
    this.__render();
  };
  DCLogic.prototype.forceUpdate = function () { this.__render(); };

  var HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;
  var WHOLE = /^\{\{\s*([^}]+?)\s*\}\}$/;

  function lookup(path, scope) {
    if (path === 'true') return true;
    if (path === 'false') return false;
    if (path === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(path)) return Number(path);
    if (/^(['"]).*\1$/.test(path)) return path.slice(1, -1);
    var parts = path.split('.');
    var v = scope[parts[0]];
    for (var i = 1; i < parts.length && v != null; i++) v = v[parts[i]];
    return v;
  }

  function interpolate(str, scope) {
    return str.replace(HOLE, function (_, p) {
      var v = lookup(p, scope);
      return v == null ? '' : String(v);
    });
  }

  function processChildren(parent, scope) {
    var kids = Array.prototype.slice.call(parent.childNodes);
    for (var i = 0; i < kids.length; i++) processNode(kids[i], scope);
  }

  function expandInto(tpl, scope) {
    var frag = document.createDocumentFragment();
    Array.prototype.forEach.call(tpl.childNodes, function (n) { frag.appendChild(n.cloneNode(true)); });
    processChildren(frag, scope);
    return frag;
  }

  function processNode(node, scope) {
    if (node.nodeType === 3) {
      if (node.nodeValue.indexOf('{{') >= 0) node.nodeValue = interpolate(node.nodeValue, scope);
      return;
    }
    if (node.nodeType !== 1) return;
    var tag = node.localName;

    if (tag === 'sc-for') {
      var m = WHOLE.exec(node.getAttribute('list') || '');
      var list = m ? lookup(m[1], scope) : null;
      var as = node.getAttribute('as') || 'item';
      var out = document.createDocumentFragment();
      (Array.isArray(list) ? list : []).forEach(function (item, idx) {
        var s = Object.create(scope);
        s[as] = item;
        s.$index = idx;
        out.appendChild(expandInto(node, s));
      });
      node.parentNode.replaceChild(out, node);
      return;
    }
    if (tag === 'sc-if') {
      var c = WHOLE.exec(node.getAttribute('value') || '');
      var ok = c ? lookup(c[1], scope) : false;
      node.parentNode.replaceChild(ok ? expandInto(node, scope) : document.createDocumentFragment(), node);
      return;
    }

    Array.prototype.slice.call(node.attributes).forEach(function (attr) {
      var val = attr.value;
      if (val.indexOf('{{') < 0) return;
      var whole = WHOLE.exec(val);
      if (/^on[a-z]+$/i.test(attr.name)) {
        node.removeAttribute(attr.name);
        var fn = whole ? lookup(whole[1], scope) : null;
        if (typeof fn === 'function') node.addEventListener(attr.name.slice(2).toLowerCase(), fn);
        return;
      }
      var name = attr.name;
      if (name.indexOf('dc-') === 0) { node.removeAttribute(name); name = name.slice(3); }
      if (whole) {
        var v = lookup(whole[1], scope);
        if (v == null || v === false) { node.removeAttribute(name); return; }
        node.setAttribute(name, v === true ? '' : String(v));
        return;
      }
      node.setAttribute(name, interpolate(val, scope));
    });
    processChildren(node, scope);
  }

  function focusPath(el, root) {
    var path = [];
    while (el && el !== root) {
      path.unshift(Array.prototype.indexOf.call(el.parentNode.children, el));
      el = el.parentNode;
    }
    return el === root ? path : null;
  }
  function fromPath(path, root) {
    var el = root;
    for (var i = 0; i < path.length && el; i++) el = el.children[path[i]];
    return el;
  }

  var WIDE = window.matchMedia('(min-width: 1024px)');
  var WIDE_CSS = [
    '.pwp-wide{max-width:none!important}',
    '.pwp-wide>header{height:72px!important;gap:24px!important;padding:0 max(40px,calc((100% - 1200px)/2))!important;background:var(--panel)}',
    '.pwp-wide>header>nav{margin-left:auto;padding:0!important;border:0!important;overflow:visible!important}',
    '.pwp-wide>header>nav a{min-height:72px!important;padding:0 14px!important;font-size:15px!important}',
    '.pwp-wide>header>button{margin-left:0!important}',
    '.pwp-wide>main{display:grid;grid-template-columns:minmax(40px,1fr) minmax(0,576px) minmax(0,576px) minmax(40px,1fr);column-gap:48px;align-items:start;padding-bottom:56px}',
    '.pwp-wide>main>*{grid-column:2/4;min-width:0;margin-left:0!important;margin-right:0!important}',
    '.pwp-wide>main>:not([data-pad]){padding-left:0!important;padding-right:0!important}',
    '.pwp-wide>main>[data-wide=left]{grid-column:2}',
    '.pwp-wide>main>[data-wide=right]{grid-column:3}',
    '.pwp-wide>main>[data-wide=bleed]{grid-column:1/-1;padding-left:max(88px,calc((100% - 1200px)/2))!important;padding-right:max(88px,calc((100% - 1200px)/2))!important}',
    '.pwp-wide>main>[data-sticky]{position:sticky;top:24px}',
    '.pwp-wide>main>[data-stack]{display:flex!important;flex-direction:column}',
    '.pwp-wide>main>[data-stack]>*{padding-left:0!important;padding-right:0!important}',
    // Past-week hero: headline on the left, standings on the right.
    '.pwp-wide [aria-labelledby=wk-title]{display:grid!important;grid-template-columns:minmax(0,7fr) minmax(0,5fr);grid-template-rows:auto auto 1fr;column-gap:64px;align-items:start;padding-top:48px!important;padding-bottom:48px!important}',
    '.pwp-wide [aria-labelledby=wk-title]>*{grid-column:1}',
    '.pwp-wide [aria-labelledby=wk-title]>svg{display:none!important}',
    '.pwp-wide [aria-labelledby=wk-title]>[role=group]{grid-column:2;grid-row:1/span 3}',
    '.pwp-wide [aria-labelledby=wk-title]>[role=group]+p{grid-column:2;grid-row:4}',
    '.pwp-wide [aria-labelledby=wk-title] h1{font-size:88px!important}',
    '.pwp-wide [aria-labelledby=ledger-h]>div:last-child{grid-template-columns:repeat(4,minmax(0,1fr))!important}',
    '.pwp-wide [aria-label=Rosters]{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px!important}',
    '.pwp-wide [aria-label=Rosters]>p{grid-column:1/-1}'
  ].join('\n');

  // Rearranges a phone-first page for a wide screen. The desktop page has its
  // own header with the menu inside it, so it is left alone.
  function applyWide(root) {
    var header = root.querySelector(':scope > header');
    var nav = root.querySelector(':scope > nav');
    if (!header || !nav) return;
    if (!document.getElementById('pwp-wide-css')) {
      var st = document.createElement('style');
      st.id = 'pwp-wide-css';
      st.textContent = WIDE_CSS;
      document.head.appendChild(st);
    }
    root.classList.add('pwp-wide');
    header.insertBefore(nav, header.querySelector('button'));
    var main = document.createElement('main');
    var footer = root.querySelector(':scope > footer');
    while (header.nextSibling && header.nextSibling !== footer) main.appendChild(header.nextSibling);
    root.insertBefore(main, footer);
    // "This week" goes straight to the desktop version instead of bouncing
    // through the phone page's redirect.
    Array.prototype.forEach.call(root.querySelectorAll('a[href="index.html"]'), function (a) {
      a.setAttribute('href', 'desktop.html');
    });
  }

  function boot() {
    var tpl = document.getElementById('dc-template');
    var scriptEl = document.querySelector('script[data-dc-script]');
    var mount = document.getElementById('dc-root');
    if (!tpl || !scriptEl || !mount) return;

    var defs = {};
    try { defs = JSON.parse(scriptEl.getAttribute('data-props') || '{}'); } catch (e) { defs = {}; }
    var props = {};
    Object.keys(defs).forEach(function (k) {
      if (k.charAt(0) !== '$' && defs[k] && 'default' in defs[k]) props[k] = defs[k]['default'];
    });
    var themed = defs.mode && defs.mode.options;
    // Until someone picks a theme, wide screens use the desktop page's light
    // theme and phones the dark one, so every page in a visit matches.
    var defaultMode = function () { return WIDE.matches ? 'light' : 'dark'; };
    var saved = readTheme();
    if (themed) props.mode = saved && themed.indexOf(saved) >= 0 ? saved : defaultMode();

    var Component = new Function('DCLogic', scriptEl.textContent + '\nreturn Component;')(DCLogic);
    var comp = new Component(props);
    comp.props = props;
    comp.state = comp.state || {};

    comp.__render = function () {
      var vals = comp.renderVals() || {};
      var active = document.activeElement;
      var focusAt = active && active !== mount && mount.contains(active) ? focusPath(active, mount) : null;
      var frag = expandInto(tpl.content, vals);
      mount.textContent = '';
      mount.appendChild(frag);

      // Pages whose theme button has no handler of its own get one here.
      var btn = mount.querySelector('header button[aria-label^="Switch"]');
      if (themed && btn && typeof vals.toggleMode !== 'function') {
        btn.addEventListener('click', function () {
          comp.setState({ mode: comp.props.mode === 'dark' ? 'light' : 'dark' });
        });
      }
      if (themed && btn) {
        btn.setAttribute('aria-label', 'Switch to ' + (comp.props.mode === 'dark' ? 'light' : 'dark') + ' mode');
      }

      var root = mount.firstElementChild;
      if (root && WIDE.matches) applyWide(root);
      if (root) {
        var bg = getComputedStyle(root).getPropertyValue('--bg').trim();
        if (bg) document.body.style.background = bg;
      }
      if (focusAt) {
        var f = fromPath(focusAt, mount);
        if (f && f.focus) f.focus();
      }
    };
    comp.__render();
    var onWidthChange = function () {
      if (themed && !readTheme()) comp.props = Object.assign({}, comp.props, { mode: defaultMode() });
      comp.__render();
    };
    if (WIDE.addEventListener) WIDE.addEventListener('change', onWidthChange);
    else if (WIDE.addListener) WIDE.addListener(onWidthChange);
    if (typeof comp.componentDidMount === 'function') comp.componentDidMount();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
