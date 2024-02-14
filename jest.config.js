/** @type {import('jest').Config} */

module.exports = {
    verbose: true,
    setupFilesAfterEnv: ['<rootDir>/jest-setup.js'],
    testEnvironment: "jest-environment-jsdom",
};
