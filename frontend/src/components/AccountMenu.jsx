import React, { useEffect, useRef, useState } from "react";

export function AccountMenu({
  activePage,
  activeProfileTab = "settings",
  currentUser,
  onOpenProfileTab,
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const showThemes = Boolean(currentUser);

  useEffect(() => {
    if (!open) return undefined;

    function handlePointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  function chooseTab(tab) {
    setOpen(false);
    onOpenProfileTab(tab, tab === "settings" ? "library" : undefined);
  }

  const items = [
    { id: "profile", label: "Profile" },
    { id: "settings", label: "Settings" },
    ...(showThemes ? [{ id: "themes", label: "Themes" }] : []),
  ];

  const menuActive = activePage === "profile";

  return (
    <div className="account-menu" ref={rootRef}>
      <button
        type="button"
        className={menuActive ? "account-chip active" : "account-chip"}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Account menu"
        onClick={() => setOpen(current => !current)}
      >
        <span>{(currentUser.display_name || currentUser.username)?.[0]?.toUpperCase()}</span>
        <strong>{currentUser.display_name || currentUser.username}</strong>
      </button>

      {open && (
        <div className="account-menu-panel" role="menu" aria-label="Account">
          <p className="account-menu-heading">Account</p>
          {items.map(item => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              className={
                menuActive && activeProfileTab === item.id
                  ? "account-menu-item active"
                  : "account-menu-item"
              }
              onClick={() => chooseTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
