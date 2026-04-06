function loadQR() {
    fetch("/get_qr")
    .then(res => res.json())
    .then(data => {

        if (data.expired) {
            alert("Session expired!");
            window.location.href = "/login";
            return;
        }

        document.getElementById("qr").src =
            "data:image/png;base64," + data.qr;

        document.getElementById("count").innerText =
            data.count + " Present";

        // TIMER
        const minutes = Math.floor(data.time_left / 60);
        const seconds = data.time_left % 60;

        document.getElementById("timer").innerText =
            `${minutes}:${seconds.toString().padStart(2, '0')}`;
    });
}

setInterval(loadQR, 5000);
loadQR();

function updateClock() {
    const now = new Date();
    const clock = document.getElementById("clock");

    if (clock) {
        clock.innerText = now.toLocaleTimeString();
    }
}

setInterval(updateClock, 1000);
updateClock();