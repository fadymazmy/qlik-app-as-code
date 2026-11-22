// Hand-written equivalent of a nebula.js UMD build: @nebula.js/stardust is external and supplied by the host.
define(['@nebula.js/stardust'], function (s) {
  'use strict';
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  return function supernova() {
    return {
      qae: { properties: { initial: { showTitles: false, qSelectionObjectDef: {} } } },
      component: function () {
        var el = s.useElement();
        var layout = s.useLayout();
        var app = s.useApp();
        var theme = s.useTheme();
        var nav = s.useNavigation();
        var sheetsP = s.usePromise(function () {
          return app.createSessionObject({
            qInfo: { qType: 'claude-sheetlist' },
            qAppObjectListDef: { qType: 'sheet', qData: { title: '/qMetaDef/title', rank: '/rank' } }
          }).then(function (o) { return o.getLayout(); });
        }, [app]);
        var sheetList = sheetsP[0];
        s.useEffect(function () {
          var items = sheetList ? sheetList.qAppObjectList.qItems.slice().sort(function (a, b) { return (a.qData.rank || 0) - (b.qData.rank || 0); }) : [];
          var current = nav && nav.getCurrentSheetId ? nav.getCurrentSheetId() : 'n/a';
          var sels = (layout.qSelectionObject && layout.qSelectionObject.qSelections) || [];
          var t = {
            name: theme && theme.name ? theme.name() : 'n/a',
            titleColor: theme.getStyle('object', 'title.main', 'color'),
            titleFont: theme.getStyle('object', 'title.main', 'fontFamily'),
            fontFamily: theme.getStyle('', '', 'fontFamily'),
            bg: theme.getStyle('object', '', 'backgroundColor'),
            varAccent: theme.getStyle('', '', '_variables.@accent'),
            customKey: theme.getStyle('', '', 'claude.accent'),
            palette0: (theme.getDataColorPalettes()[0] || {}).key
          };
          var html = '<div style="font:13px/1.4 ' + esc(t.fontFamily || 'sans-serif') + ';color:' + esc(t.titleColor || '#000') + ';padding:6px">' +
            '<div data-k="tabs">' + items.map(function (i) {
              var on = i.qInfo.qId === current;
              return '<button data-sheet="' + esc(i.qInfo.qId) + '" style="margin:2px;padding:4px 8px;border:0;border-bottom:2px solid ' + (on ? '#1aa865' : 'transparent') + ';background:none;color:inherit;cursor:pointer">' + esc(i.qData.title) + '</button>';
            }).join('') + '</div>' +
            '<div>current sheet: <b>' + esc(current) + '</b> | navigation api: ' + esc(nav ? Object.keys(Object.getPrototypeOf(nav) || {}).concat(Object.keys(nav)).join(',') : 'none') + '</div>' +
            '<div>selections: ' + (sels.length ? sels.map(function (x) { return esc(x.qField) + '=' + esc(x.qSelected); }).join('; ') : 'none') +
            ' <button data-k="clear" style="cursor:pointer">Clear all</button></div>' +
            '<div>theme: ' + esc(JSON.stringify(t)) + '</div></div>';
          el.innerHTML = html;
          el.querySelectorAll('button[data-sheet]').forEach(function (b) {
            b.onclick = function () { if (nav && nav.goToSheet) { nav.goToSheet(b.getAttribute('data-sheet')); } };
          });
          el.querySelector('button[data-k="clear"]').onclick = function () { app.clearAll(); };
        }, [layout, sheetList, theme, nav]);
      }
    };
  };
});
