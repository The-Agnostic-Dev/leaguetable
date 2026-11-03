// Result form: "Add scorer" / "Add card" append a blank row to the matching
// Django formset and bump its TOTAL_FORMS counter.
(function () {
  function addRow(prefix) {
    const template = document.getElementById(`${prefix}-empty-form`)
    const total = document.getElementById(`id_${prefix}-TOTAL_FORMS`)
    const container = document.getElementById(`${prefix}-rows`)
    const index = Number(total.value)
    const holder = document.createElement('div')
    holder.innerHTML = template.innerHTML.replaceAll('__prefix__', String(index))
    const row = holder.firstElementChild
    container.appendChild(row)
    total.value = String(index + 1)
    const select = row.querySelector('select')
    if (select) select.focus()
  }

  document.querySelectorAll('[data-add-row]').forEach((button) => {
    button.addEventListener('click', () => addRow(button.dataset.addRow))
  })
})()
