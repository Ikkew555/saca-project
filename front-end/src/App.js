import { BrowserRouter, Routes, Route } from "react-router-dom";
import Acknowledgment from "./acknowledgment";
import Home from "./home";
import Chatbot from "./chat";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Splash page shows first */}
        <Route path="/" element={<Acknowledgment />} />

        {/* Main website */}
        <Route path="/home" element={<Home />} />
        <Route path="/chatbot" element={<Chatbot />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
