// hlbb mapa: click a part on the board = toggle "Placed" for that single piece.
(function () {
  var CB = "Placed";

  function bomIds() {
    var ids = new Set();
    for (var row of pcbdata.bom.both) for (var r of row) ids.add(r[1]);
    return ids;
  }

  function placedSet() { return getStoredCheckboxRefs(CB); }

  function updateCounter() {
    var el = document.getElementById("hlbb-licznik");
    if (!el) return;
    var all = bomIds(), placed = placedSet(), done = 0;
    for (var id of all) if (placed.has(id)) done++;
    var left = all.size - done;
    el.classList.toggle("hlbb-gotowe", left === 0);
    el.textContent = left === 0
      ? "Wszystko przylutowane ✓ (" + all.size + ")"
      : "Zostało " + left + " z " + all.size;
  }

  function toggle(id) {
    var set = placedSet();
    if (set.has(id)) set.delete(id); else set.add(id);
    settings.checkboxStoredRefs[CB] = Array.from(set).join(",");
    writeStorage("checkbox_" + CB, settings.checkboxStoredRefs[CB]);
    setMarkWhenChecked(CB);          // repaints marks + table
    updateCheckboxStats(CB);
    if (id in footprintIndexToHandler) {
      footprintIndexToHandler[id]();  // keep the clicked part highlighted
      smoothScrollToRow(currentHighlightedRowId);
    }
    updateCounter();
  }

  var original = footprintsClicked;
  footprintsClicked = function (footprintIndexes) {
    var clickable = footprintIndexes.filter(function (i) { return i in footprintIndexToHandler; });
    original(footprintIndexes);
    if (clickable.length === 0) return;   // e.g. a part filtered out of the list
    toggle(lastClicked);
  };

  window.addEventListener("load", function () {
    var top = document.getElementById("top");
    if (top && !document.getElementById("hlbb-licznik")) {
      var el = document.createElement("div");
      el.id = "hlbb-licznik";
      el.title = "Kliknij część na obrazku płytki, żeby ją odhaczyć jako przylutowaną (drugi klik cofa).";
      top.insertBefore(el, top.firstChild.nextSibling);
    }
    if (settings.markWhenChecked !== CB) setMarkWhenChecked(CB);
    EventHandler.registerCallback(IBOM_EVENT_TYPES.CHECKBOX_CHANGE_EVENT, updateCounter);
    updateCounter();
  });
})();
