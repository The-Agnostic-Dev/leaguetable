// Filters the players table as you type, matching on player and team name.
(function () {
  const input = document.getElementById('player-search')
  const rows = Array.from(document.querySelectorAll('#player-table tbody tr'))
  const count = document.getElementById('player-count')
  const empty = document.getElementById('no-matches')
  if (!input) return

  function applyFilter() {
    const query = input.value.trim()
    let shown = 0
    rows.forEach((row) => {
      const match = query === '' || row.dataset.search.includes(query)
      row.hidden = !match
      if (match) shown += 1
    })
    count.textContent = String(shown)
    empty.hidden = shown !== 0
  }

  input.addEventListener('input', applyFilter)
  const initial = new URLSearchParams(window.location.search).get('q')
  if (initial) {
    input.value = initial
    applyFilter()
  }
})()
