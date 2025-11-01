function loadBooks() {
  fetch("/books")
    .then(res => res.json())
    .then(data => {
      document.getElementById("books").innerHTML =
        "<h3>Books:</h3>" + data.map(b => `<p>${b.title} - ${b.genre}</p>`).join('');
    });
}

function loadRecommendations() {
  fetch("/recommendations")
    .then(res => res.json())
    .then(data => {
      document.getElementById("recommendations").innerHTML =
        "<h3>Recommendations:</h3>" + data.map(r => `<p>${r}</p>`).join('');
    });
}

function loadCache() {
  fetch("/cache")
    .then(res => res.json())
    .then(data => {
      document.getElementById("cache").innerHTML =
        "<h3>Cache Data:</h3><pre>" + JSON.stringify(data, null, 2) + "</pre>";
    });
}

document.addEventListener('DOMContentLoaded', function() {
  const tierSelect = document.getElementById('tier');
  const premiumFields = document.getElementById('premiumFields');

  if (tierSelect) {
    tierSelect.addEventListener('change', function() {
      if (tierSelect.value === 'Premium') {
        premiumFields.style.display = 'block';
      } else {
        premiumFields.style.display = 'none';
      }
    });
  }
});
