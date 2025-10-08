import { useNavigate } from "react-router-dom";
import "./acknowledgment.css";

const Acknowledgment = () => {
  const navigate = useNavigate();

  return (
    <div className="acknowledgment">
      <div className="acknowledgment-content">
        <h1>Acknowledgment of Country</h1>
        <p>
          We acknowledge the Traditional Custodians of the land on which we live
          and work. We pay our respects to Elders past, present and emerging,
          and recognise their continuing connection to culture, community, and
          Country.
        </p>
        <button
          className="acknowledgment-btn"
          onClick={() => navigate("/home")}
        >
          Continue to website
        </button>
      </div>

      <footer className="acknowledgment-footer">
        © 2025 Health Service App. All rights reserved.
      </footer>
    </div>
  );
};

export default Acknowledgment;
