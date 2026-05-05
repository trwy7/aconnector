const forms = document.querySelectorAll("form")

forms.forEach(form => {
    form.addEventListener('submit', function(e) {
        form.classList.add("submitted")
    })
})

window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        const forms = document.querySelectorAll("form");
        forms.forEach(form => {
            form.classList.remove("submitted");
        });
    }
});