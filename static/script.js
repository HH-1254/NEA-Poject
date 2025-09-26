// document.addEventListener("DOMContentLoaded", () => {
//     const toggle = document.getElementById("darkModeToggle");
//     const body = document.body;

//     // Load saved theme
//     if (localStorage.getItem("theme") === "dark") {
//         body.classList.add("dark-mode");
//         toggle.checked = true;
//     }

//     toggle.addEventListener("change", () => {
//         if (toggle.checked) {
//             body.classList.add("dark-mode");
//             localStorage.setItem("theme", "dark");
//         } else {
//             body.classList.remove("dark-mode");
//             localStorage.setItem("theme", "light");
//         }
//     });
// });




// <link rel="stylesheet" href="{{ url_for('static', filename='script.js') }}"> - Head

// <label>
//         <input type="checkbox" id="darkModeToggle"> Dark Mode
//     </label>

//     <script src="{{ url_for('static', filename='script.js') }}"></script> - Body