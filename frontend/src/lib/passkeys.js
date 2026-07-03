// Passkey/WebAuthn helpers for Origin Lock release sealing.
//
// Passkeys verify the artist on-device using the operating system's biometric
// or PIN prompt. That verification never leaves the device: IndieFund does not
// receive or store Face ID, Touch ID, fingerprints, or any biometric data. Only
// public-key material and opaque challenge strings are exchanged.
//
// This is placeholder-ready architecture. Registration and authentication issue
// and consume server challenges; full cryptographic signature verification is
// wired in a follow-up. Every browser call is guarded so callers can fall back
// to the password path when passkeys are unavailable or not yet registered.

export function passkeysSupported() {
  return typeof window !== "undefined" && typeof window.PublicKeyCredential !== "undefined";
}

export async function beginPasskeyAuth(apiFetch) {
  try {
    const res = await apiFetch("/originlock/passkeys/authenticate/begin/", { method: "POST" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// Returns { challenge, credential_id } for the seal request, or null when no
// passkey is available so the caller falls back to the password prompt.
export async function requestPasskeyAssertion(apiFetch) {
  const begin = await beginPasskeyAuth(apiFetch);
  if (!begin || !Array.isArray(begin.credential_ids) || begin.credential_ids.length === 0) {
    return null;
  }
  return { challenge: begin.challenge, credential_id: begin.credential_ids[0] };
}

export async function listPasskeys(apiFetch) {
  try {
    const res = await apiFetch("/originlock/passkeys/");
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  } catch {
    return [];
  }
}
