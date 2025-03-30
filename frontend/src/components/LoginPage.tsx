import React, { useState } from 'react';
import api from '../api/axios';

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const response = await api.post('/login', {
        username,
        password
      });
      const token = response.data.access_token;
      if (token) {
        localStorage.setItem('token', token);
        alert('Authentification réussie !');
        window.location.href = '/settings'; 
      }
    } catch (err: any) {
      console.error(err);
      setError('Identifiants invalides');
    }
  };

  return (
    <div className="max-w-sm mx-auto p-4">
      <h2 className="text-xl mb-4">Admin Login</h2>
      <form onSubmit={handleLogin} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="border p-2 w-full"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border p-2 w-full"
          />
        </div>
        {error && <p className="text-red-500">{error}</p>}
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Se connecter
        </button>
      </form>
    </div>
  );
};

export default LoginPage;
