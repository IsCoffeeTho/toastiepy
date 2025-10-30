var preloaded = document.onload ?? window.onload;

document.onload = window.onload = () => {
	if (preloaded)
		preloaded();
	var words = [
		"apple",
		"river",
		"mountain",
		"city",
		"car",
		"computer",
		"book",
		"garden",
		"window",
		"chair",
		"teacher",
		"student",
		"bridge",
		"camera",
		"coffee",
		"planet",
		"forest",
		"animal",
		"music",
		"cloud",
		"train",
		"door",
		"flower",
		"island",
		"machine",
		"painting",
		"desk",
		"road",
		"ocean",
		"clock",
		"bottle",
		"library",
		"engine",
		"village",
		"market",
		"tree",
		"storm",
		"language",
		"phone",
		"station",
		"riverbank",
		"journal",
		"mirror",
		"signal",
		"ship",
		"house",
		"street",
		"valley",
		"museum",
		"shadow",
		"dream",
	];

	var randomEndpoint = "";
	for (var i = 0; i < 3; i++) {
		var selection = Math.floor(Math.random() * words.length);
		var word = words.splice(selection, 1)[0];
		word = word[0].toUpperCase() + word.slice(1).toLowerCase();
		randomEndpoint += word;
	}
	document.getElementById("rand404").attributes.href.value = `${window.location}/${randomEndpoint}`;
};
