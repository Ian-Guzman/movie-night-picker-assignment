const randomButton = document.getElementById("random-button");
const randomMovie = document.getElementById("random-movie");

randomButton.addEventListener("click", function () {

    fetch("https://movie-night-picker-api-h4fgezabg6dbatgu.mexicocentral-01.azurewebsites.net/api/movie")
        .then(response => response.json())
        .then(data => {
            randomMovie.textContent = data.movie;
        })
        .catch(error => {
            console.error("Error:", error);
            randomMovie.textContent = "Could not load a movie.";
        });

});


const genreForm = document.getElementById("genre-form");
const genreSelect = document.getElementById("genre");
const recommendation = document.getElementById("recommendation");

genreForm.addEventListener("submit", function (event) {

    event.preventDefault();
    
    const selectedGenre = genreSelect.value;

    // Client-side input validation
    const allowedGenres = ["action", "comedy", "horror", "sci-fi"];

    if (!allowedGenres.includes(selectedGenre)) {
        recommendation.textContent = "Please select a valid genre.";
        return;
    }

    fetch("https://movie-night-picker-api-h4fgezabg6dbatgu.mexicocentral-01.azurewebsites.net/api/recommend", {
        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            genre: selectedGenre
        })
    })
        .then(response => response.json())
        .then(data => {
            recommendation.textContent = data.movie;
        })
        .catch(error => {
            console.error("Error:", error);
            recommendation.textContent = "Could not get a recommendation.";
        });

});

// Google OpenID Connect login
const googleSignInButton = document.getElementById("google-signin-button");
const logoutButton = document.getElementById("logout-button");
const userGreeting = document.getElementById("user-greeting");

let googleIdToken = null;

function handleGoogleLogin(response) {
    // Send Google's identity token to Flask for verification.
    fetch(
        "https://movie-night-picker-api-h4fgezabg6dbatgu.mexicocentral-01.azurewebsites.net/api/auth/google",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                credential: response.credential
            })
        }
    )
    .then(async response => {
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Login failed");
        }

        return data;
    })
    .then(data => {
        googleIdToken = response.credential;
        userGreeting.textContent = "Hello, " + data.name + "!";
        googleSignInButton.hidden = true;
        logoutButton.hidden = false;
    })
    .catch(error => {
        console.error("Google login error:", error);
        userGreeting.textContent = "Sign-in failed. Please try again.";
    });
}

function initializeGoogleLogin() {
    if (!window.google || !google.accounts || !google.accounts.id) {
        userGreeting.textContent = "Google sign-in is unavailable.";
        return;
    }

    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLogin
    });

    google.accounts.id.renderButton(
        googleSignInButton,
        {
            theme: "outline",
            size: "large",
            text: "signin_with"
        }
    );
}

logoutButton.addEventListener("click", function () {
    googleIdToken = null;
    google.accounts.id.disableAutoSelect();

    userGreeting.textContent = "";
    googleSignInButton.hidden = false;
    logoutButton.hidden = true;
});

window.addEventListener("load", initializeGoogleLogin);
