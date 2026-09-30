// Viser en lenke til adminpanelet i hovednavigasjonen for innloggede admin-brukere.
(function () {
	fetch("/api/me", { credentials: "same-origin" })
		.then(function (response) {
			return response.ok ? response.json() : null;
		})
		.then(function (me) {
			if (!me || !me.is_admin) {
				return;
			}
			var nav = document.querySelector("header nav");
			if (!nav) {
				return;
			}
			var link = document.createElement("a");
			link.href = "/admin/";
			link.textContent = "Adminpanel";
			nav.appendChild(link);
		})
		.catch(function () {});
})();
