import React from "react";

export function ProfileSettingsNav({ activeSection = "library", onChange, sections = [] }) {
  if (sections.length === 0) return null;

  return (
    <nav className="profile-settings-nav" aria-label="Settings">
      <p className="profile-settings-nav-label">Settings</p>
      {sections.map(section => (
        <button
          key={section.id}
          type="button"
          className={activeSection === section.id ? "profile-settings-nav-item active" : "profile-settings-nav-item"}
          aria-current={activeSection === section.id ? "page" : undefined}
          onClick={() => onChange(section.id)}
        >
          {section.label}
        </button>
      ))}
    </nav>
  );
}
