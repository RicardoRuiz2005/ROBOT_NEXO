/* LÍNEAS ANIMADAS RGB GRADIENT */
tsParticles.load("particles", {
  fpsLimit: 120,
  interactivity: {
    events: {
      onClick: { enable: true, mode: "push" },
      onHover: { enable: true, mode: "repulse" },
      resize: true
    },
    modes: {
      push: { quantity: 4 },
      repulse: { distance: 100, duration: 0.4 }
    }
  },

  particles: {
    /* Bolitas multicolor */
    color: {
      value: ["#FFD700", "#00FF00", "#FF0000", "#2762EA"]
    },

    /* ✨ LÍNEAS ANIMADAS RGB SUAVE ✨ */
    links: {
      enable: true,
      distance: 150,
      width: 1.8,
      opacity: 0.8,

      /* colores dinámicos */
      color: {
        value: "random"
      },

      /* animación de color */
      blink: false,
      consent: false
    },

    move: {
      direction: "none",
      enable: true,
      outModes: { default: "bounce" },
      speed: 1
    },

    number: {
      density: { enable: true, area: 800 },
      value: 85
    },

    opacity: { value: 0.7 },
    shape: { type: "circle" },
    size: { value: { min: 1, max: 3 } }
  },

  detectRetina: true
});
