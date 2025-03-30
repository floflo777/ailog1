import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import ChatPage from './components/ChatPage';
import SettingsPage from './components/SettingsPage';
import LoginPage from './components/LoginPage';
import AdminPage from './components/AdminPage';

function App() {

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-blue-600 text-white p-4 mb-8">
          <h1 className="text-2xl font-bold">CustomGPT</h1>
          <nav className="mt-4 space-x-4">
            <Link
              to="/"
              className="hover:text-gray-200 transition-colors"
            >
              Document Analysis
            </Link>
            <Link
              to="/chat"
              className="hover:text-gray-200 transition-colors"
            >
              RAG Chat
            </Link>
            <Link
              to="/settings"
              className="hover:text-gray-200 transition-colors"
            >
              Settings
            </Link>
            <Link
              to="/login"
              className="hover:text-gray-200 transition-colors"
            >
              Login
            </Link>

            {/*
            */}
            <Link
              to="/admin"
              className="hover:text-gray-200 transition-colors"
            >
              Superadmin
            </Link>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<ChatInterface />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Nouvelle route pour la page Admin */}
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
