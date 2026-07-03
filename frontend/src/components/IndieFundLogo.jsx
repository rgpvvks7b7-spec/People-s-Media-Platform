import React from "react";

export function IndieFundLogo({ asButton = false, className = "", type = "button", ...props }) {
  const classes = ["indiefund-brand", className].filter(Boolean).join(" ");
  const content = (
    <>
      <span className="indiefund-brand__indie">INDIE</span>
      <span className="indiefund-brand__fund">FUND</span>
    </>
  );

  if (asButton) {
    return (
      <button type={type} className={classes} {...props}>
        {content}
      </button>
    );
  }

  return (
    <span className={classes} {...props}>
      {content}
    </span>
  );
}
