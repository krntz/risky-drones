var socket = new WebSocket('ws://' + location.host + '/action');
socket.addEventListener('open', function (event) {
    console.log("[open] Connection established");
});

socket.addEventListener('message', function (event) {
    var data = JSON.parse(event.data);
    switch(data.action){
        case 'score':
            document.getElementById('score').textContent = + data.value;
            break;
        case 'finish':
            document.getElementById('surveyText').innerHTML = data.message;
            document.getElementById('surveyModal').style.display = 'block';
            break;
        case 'failure':
            document.getElementById('failureText').innerHTML = data.message;
            document.getElementById('failureAlert').style.display = 'block';
            setTimeout(function () {
                failureAlert.style.display = 'none';
            }, 8000);
            break;
        case 'welcome':
            document.getElementById('alertText').innerHTML = data.message;
            document.getElementById('customAlert').style.display = 'block';
            setTimeout(function () {
                customAlert.style.display = 'none';
            }, 8000);
            break;
        case 'goal':
            document.getElementById('alertText').innerHTML = data.message;
            document.getElementById('customAlert').style.display = 'block';
            setTimeout(function () {
                customAlert.style.display = 'none';
            }, 3000);
            break;
        case 'start timer':
            startTimer();
            break;
        case 'stop timer':
            stopTimer();
            break;
        default:
            console.log("recieved unknown action type: " + data.action);
    }

});
function hideAllButtons(duration) {
    // Get all buttons
    var buttons = document.querySelectorAll("button");

    // Add a 'hide' class to all buttons
    buttons.forEach(function(btn) {
        btn.classList.add("hide");
    });

    // Remove the 'hide' class after duration
    setTimeout(function() {
        buttons.forEach(function(btn) {
            btn.classList.remove("hide");
        });
    }, duration);
}

function sendMessage(actionType, parameter) {
    var message = "";
    switch(actionType) {
        case 'move':
            message = JSON.stringify(
                { "action": actionType, "direction": parameter }
            );

            hideAllButtons(2000);

            break;
        case 'take off':
            message = JSON.stringify(
                { "action": actionType }
            );

            document.getElementById('tolBtn').value = "land";
            document.getElementById('tolBtn').innerHTML = "Land";

            startTimer();

            hideAllButtons(2000);

            break;
        case 'land':
            message = JSON.stringify(
                { "action": actionType }
            );

            document.getElementById('tolBtn').value = "Take Off";
            document.getElementById('tolBtn').innerHTML = "Take Off";

            stopTimer();

            hideAllButtons(2000);

            break;
        case 'failed trial':
            message = JSON.stringify(
                { "action": actionType }
            );

            hideAllButtons(2000);

            break;
        default:
            console.log("trying to send unknown action type: " + actionType); 
    }
    socket.send(message); // Send the message to the server
}

