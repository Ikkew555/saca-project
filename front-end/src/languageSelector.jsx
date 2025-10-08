import { useState } from "react";
import usFlag from "./assets/flags/eng.png";
import auFlag from "./assets/flags/au.png";

const LanguageSelector = ({ language, onChange }) => {
  const [open, setOpen] = useState(false);

  const options = [
    { value: "en-US", label: "English (US)", flag: usFlag },
    { value: "kriol", label: "Kriol (AU)", flag: auFlag },
  ];

  // ✅ Fallback if no match found
  const selected = options.find((opt) => opt.value === language) || options[0];

  return (
    <div className="custom-select">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="custom-select-btn"
      >
        <img src={selected.flag} alt={selected.label} className="flag-icon" />
        {selected.label}
      </button>

      {open && (
        <ul className="custom-select-list">
          {options.map((opt) => (
            <li
              key={opt.value}
              onClick={() => {
                onChange(opt.value); // updates language in HomePage
                setOpen(false);
              }}
            >
              <img src={opt.flag} alt={opt.label} className="flag-icon" />
              {opt.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default LanguageSelector;
