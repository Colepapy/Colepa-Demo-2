const webhookUrl = "https://mgcapra314.app.n8n.cloud/webhook/Colepa2025";

function agregarMensaje(texto, tipo) {
  const chat = document.getElementById("chat");
  const msg = document.createElement("div");
  msg.className = `message ${tipo}`;
  msg.textContent = texto;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

async function enviarPregunta() {
  const input = document.getElementById("userInput");
  const pregunta = input.value.trim();
  if (!pregunta) return;

  agregarMensaje(pregunta, "user");
  input.value = "";
  agregarMensaje("Procesando...", "bot");

  try {
    const res = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta }),
    });

    const data = await res.json();
    const respuesta = data?.respuesta || JSON.stringify(data);
    document.querySelectorAll(".bot").pop().remove(); // Quita "Procesando..."
    agregarMensaje(respuesta, "bot");
  } catch (error) {
    document.querySelectorAll(".bot").pop().remove();
    agregarMensaje("❌ Error al conectar con el servidor", "bot");
  }
}
