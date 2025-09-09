import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import HomePage from "./pages/HomePage";
import AskAnythingPage from "./pages/AskAnythingPage";
import axios from "axios";

// Set axios baseURL to /api to match proxy
axios.defaults.baseURL = "/api";

function App() {
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);

  React.useEffect(() => {
    // Check auth by calling /health or /user/github-config
    axios
      .get("/user/github-config", { withCredentials: true })
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false));
  }, []);

  return (
    <Router>
      <nav className="bg-gray-800 p-4 text-white flex space-x-4">
        {isAuthenticated ? (
          <>
            <Link to="/" className="hover:underline">
              Home
            </Link>
            <Link to="/ask" className="hover:underline">
              Ask Anything
            </Link>
            <button
              onClick={() => {
                axios.post("/logout", {}, { withCredentials: true }).then(() => {
                  setIsAuthenticated(false);
                });
              }}
              className="hover:underline"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="hover:underline">
              Login
            </Link>
            <Link to="/signup" className="hover:underline">
              Signup
            </Link>
          </>
        )}
      </nav>
      <div className="p-4">
        <Routes>
          <Route
            path="/login"
            element={
              isAuthenticated ? <Navigate to="/" /> : <LoginPage onLogin={() => setIsAuthenticated(true)} />
            }
          />
          <Route
            path="/signup"
            element={
              isAuthenticated ? <Navigate to="/" /> : <SignupPage onSignup={() => setIsAuthenticated(true)} />
            }
          />
          <Route
            path="/"
            element={isAuthenticated ? <HomePage /> : <Navigate to="/login" />}
          />
          <Route
            path="/ask"
            element={isAuthenticated ? <AskAnythingPage /> : <Navigate to="/login" />}
          />
          <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/login"} />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
