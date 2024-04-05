module.exports = {
  ci: {
    collect: {
      url: ["http://localhost:8000/"],
      startServerCommand: "docker-compose up --build",
    },
    upload: { target: "temporary-public-storage" },
  },
};
