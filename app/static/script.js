const forms = document.querySelectorAll("form")

forms.forEach(form => {
    form.addEventListener('submit', function(e) {
        form.classList.add("submitted")
    })
})