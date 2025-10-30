function log(str) {
	var colorWrapper = document.createElement("div");
	colorWrapper.style.color = "#88f";
	colorWrapper.innerText += `${str}`
	document.getElementById("conn").appendChild(colorWrapper);
}

function clientlog(str) {
	var colorWrapper = document.createElement("div");
	colorWrapper.innerText += `${str}`
	document.getElementById("conn").appendChild(colorWrapper);
}

function serverlog(str) {
	var colorWrapper = document.createElement("div");
	colorWrapper.style.color = "#ff8";
	colorWrapper.innerText += `${str}`
	document.getElementById("conn").appendChild(colorWrapper);
}

document.onload = window.onload = () => {
	log("Connecting to '/echo-ws'...")
	const socket = new WebSocket('/echo-ws');
	socket.onerror = function(err) {
		log("There was an error trying to connect");
	};
	socket.onopen = function() {
		var inputElem = document.getElementById("input")
		inputElem.disabled = false;
		inputElem.onkeydown = (ev) => {
			if (ev.key == "Enter") {
				clientlog(inputElem.value)
				socket.send(inputElem.value)
				inputElem.value = "";
			}
		}
		inputElem.focus();
		socket.onmessage = function(message) {
			serverlog(message.data)
			inputElem.disabled = false;
		}
	}
	
}