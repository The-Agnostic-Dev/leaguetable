// "Show more" on the top scorers table loads the next slice from the server
// and inserts it above the button row.
(function () {
  const table = document.getElementById('scorers')
  const button = document.getElementById('show-more')
  if (!table || !button) return
  const tbody = table.tBodies[0]
  const moreRow = button.closest('tr')

  button.addEventListener('click', async () => {
    button.disabled = true
    const offset = tbody.querySelectorAll('tr').length
    try {
      const response = await fetch(`${table.dataset.moreUrl}?offset=${offset}`, {
        headers: { Accept: 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      moreRow.insertAdjacentHTML('beforebegin', data.html)
      if (data.has_more) {
        button.disabled = false
      } else {
        moreRow.remove()
      }
    } catch (error) {
      button.disabled = false
      button.textContent = 'Try again'
      console.error(error)
    }
  })
})()
