import { BrowserRouter, Routes, Route } from "react-router-dom";
import Acknowledgment from "./acknowledgment";
import Home from "./home";
import Chatbot from "./chat";
import ResultPage from "./result";
import SuggestionPage from "./suggestion";
import Layout from "./Layout";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          {/* Splash page shows first */}
          <Route index element={<Chatbot />} />
          <Route path="/result" element={<ResultPage />} />
          <Route path="/suggestions" element={<SuggestionPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
