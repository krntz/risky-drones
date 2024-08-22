var socket = new WebSocket('ws://' + location.host + '/action');
socket.addEventListener('open', function (event) {
    console.log("[open] Connection established");
});

socket.addEventListener('message', function (event) {
    var message = JSON.parse(event.data);
    switch(message.action){
        case 'score':
            document.getElementById('score').textContent = message.data;
            break;
        case 'failure':
            document.getElementById('failureText').innerHTML = message.data;
            document.getElementById('failureAlert').style.display = 'block';
            setTimeout(function () {
                failureAlert.style.display = 'none';
            }, 8000);
            break;
        case 'alert':
            var modalDuration = 0;

            switch(message.type) {
                case 'no takeoff':
                    modalDuration = 4000;
                    document.getElementById('tolBtn').value = "take off";
                    document.getElementById('tolBtn').innerHTML = "Take Off";

                    break;
                case 'na':
                    modalDuration = 8000;
                    break;
                default:
                    console.log("Recieved unknown type: " + message.type);
            }

            document.getElementById('alertText').innerHTML = message.data;
            document.getElementById('customAlert').style.display = 'block';

            setTimeout(function () {
                customAlert.style.display = 'none';
            }, modalDuration);

            break;
        case 'goal':
            document.getElementById('alertText').innerHTML = message.data;
            document.getElementById('customAlert').style.display = 'block';
            setTimeout(function () {
                customAlert.style.display = 'none';
            }, 3000);
            break;
        case 'timer':
            if(message.data == "start") {
                startTimer();
            } else if (message.data == "stop") {
                stopTimer();
            } else {
                console.log("Unknown timer data: " + message.data);
            }
            break;
        default:
            console.log("Recieved unknown action type: " + message.action);
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

            hideAllButtons(2000);

            break;
        case 'land':
            message = JSON.stringify(
                { "action": actionType }
            );

            document.getElementById('tolBtn').value = "take off";
            document.getElementById('tolBtn').innerHTML = "Take Off";

            hideAllButtons(2000);

            break;
        case 'out of time':
            message = JSON.stringify(
                { "action": actionType }
            );

            document.getElementById('tolBtn').value = "take off";
            document.getElementById('tolBtn').innerHTML = "Take Off";

            hideAllButtons(2000);

            break;
        default:
            console.log("trying to send unknown action type: " + actionType); 
    }
    socket.send(message); // Send the message to the server
}

