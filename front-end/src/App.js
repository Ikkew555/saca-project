import { BrowserRouter, Routes, Route } from "react-router-dom";
import Acknowledgment from "./acknowledgment";
import Home from "./home";
import Chatbot from "./chat";
import ResultPage from "./result";
import SuggestionPage from "./suggestion";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Splash page shows first */}
        <Route path="/" element={<Chatbot />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="/suggestions" element={<SuggestionPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
