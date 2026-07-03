import React from "react";

export function ProfileAccountNav({ activeTab = "account", onChange, showThemes = false }) {
  const tabs = [
    { id: "profile", label: "Profile" },
    { id: "settings", label: "Settings" },
    ...(showThemes ? [{ id: "themes", label: "Themes" }] : []),
  ];

  return (
    <nav className="profile-account-nav" aria-label="Account sections">
      {tabs.map(tab => (
        <button
          key={tab.id}
          type="button"
          className={activeTab === tab.id ? "nav-pill active" : "nav-pill"}
          aria-current={activeTab === tab.id ? "page" : undefined}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
