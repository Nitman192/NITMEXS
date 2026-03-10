(() => {
  const target = document.getElementById("version-badge");
  if (!target) {
    return;
  }

  fetch("/system/version")
    .then((response) => response.json())
    .then((payload) => {
      target.textContent = payload?.data?.version ?? "n/a";
    })
    .catch(() => {
      target.textContent = "unreachable";
    });
})();
