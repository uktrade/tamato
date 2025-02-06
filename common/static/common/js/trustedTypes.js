import DOMPurify from "dompurify";

/**
 * Creates a default Trusted Types policy that serves as a fallback policy
 * to sanitise direct sink usage in third-party dependencies.
 */
if (typeof window.trustedTypes !== "undefined") {
  window.trustedTypes.createPolicy("default", {
    createHTML: (to_escape) =>
      DOMPurify.sanitize(to_escape, { RETURN_TRUSTED_TYPE: true }),
  });
}
