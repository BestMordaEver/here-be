for (element of document.getElementsByClassName('fading')) {
	element.addEventListener('transitionend', function (event) {
		if (event.propertyName == 'opacity') {
			this.classList.add('invisible')
			this.nextElementSibling.classList.toggle('invisible')
		}
	})
}

let properties = []

for (button of document.getElementsByClassName('primary')) {
	button.addEventListener('click', function () {
		if (this.name) properties.push(this.name)
		if (!this.classList.contains('submit')) this.parentElement.classList.add('faded')
	})
}

for (button of document.getElementsByClassName('submit')) {
	button.addEventListener('click', async (event) => {
		console.log(properties)
		event.preventDefault();
	
		const response = await fetch('https://here-be.vercel.app/api/submit', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(properties),
		});

		if (response.ok) {
			window.location.replace('/dragon-submitted.html')
		} else {
			alert('Error submitting action.');
		}
	})
}
