import React, { useEffect, useState } from 'react';
import api from '../api/axios';

interface User {
  id: number;
  username: string;
  role: string;
}

interface CollectionItem {
  id: number;
  name: string;
  description?: string;
}

const AdminPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [newUserUsername, setNewUserUsername] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState<'admin' | 'superadmin'>('admin');
  const [allCollections, setAllCollections] = useState<CollectionItem[]>([]);
  const [expandedUserId, setExpandedUserId] = useState<number | null>(null);
  const [userCollections, setUserCollections] = useState<{
    [userId: number]: CollectionItem[];
  }>({});
  const [selectedCollectionToAssign, setSelectedCollectionToAssign] = useState<{
    [userId: number]: number; 
  }>({});

  const fetchUsers = async () => {
    try {
      const response = await api.get('/admin/users');
      setUsers(response.data);
    } catch (error) {
      console.error(error);
      alert("Erreur lors du chargement des utilisateurs");
    }
  };

  const fetchAllCollections = async () => {
    try {
      const res = await api.get('/admin/collections');
      if (res.data && res.data.collections) {
        setAllCollections(res.data.collections);
      }
    } catch (error) {
      console.error(error);
      alert("Erreur lors du chargement des collections");
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchAllCollections();
  }, []);

  const handleCreateUser = async () => {
    if (!newUserUsername.trim() || !newUserPassword.trim()) {
      alert("Veuillez renseigner un username et un password.");
      return;
    }

    try {
      await api.post('/admin/create-admin', {
        username: newUserUsername,
        password: newUserPassword,
        role: newUserRole
      });
      alert("Utilisateur créé avec succès !");
      setNewUserUsername('');
      setNewUserPassword('');
      setNewUserRole('admin');
      fetchUsers();
    } catch (error) {
      console.error(error);
      alert("Erreur lors de la création de l'utilisateur");
    }
  };

  const handleDeleteUser = async (id: number) => {
    if (!window.confirm("Supprimer cet utilisateur ?")) return;
    try {
      await api.delete(`/admin/users/${id}`);
      alert("Utilisateur supprimé !");
      fetchUsers();
    } catch (error) {
      console.error(error);
      alert("Erreur lors de la suppression");
    }
  };

  const loadUserCollections = async (userId: number) => {
    try {
      const res = await api.get(`/admin/users/${userId}/collections`);
      setUserCollections((prev) => ({
        ...prev,
        [userId]: res.data
      }));
    } catch (error) {
      console.error(error);
      alert("Erreur lors du chargement des collections de l'utilisateur");
    }
  };

  const toggleUserCollections = (userId: number) => {
    if (expandedUserId === userId) {
      setExpandedUserId(null);
    } else {
      setExpandedUserId(userId);
      loadUserCollections(userId);
    }
  };

  const handleAssignCollection = async (userId: number) => {
    const collId = selectedCollectionToAssign[userId];
    if (!collId) {
      alert("Veuillez sélectionner une collection");
      return;
    }
    try {
      await api.post(`/admin/assign-collection?user_id=${userId}&collection_id=${collId}`);
      alert("Collection assignée !");
      loadUserCollections(userId);
    } catch (error) {
      console.error(error);
      alert("Erreur lors de l'assignation de la collection");
    }
  };

  const handleUnassignCollection = async (userId: number, collectionId: number) => {
    if (!window.confirm("Retirer cette collection de l'utilisateur ?")) return;
    try {
      await api.delete(`/admin/unassign-collection?user_id=${userId}&collection_id=${collectionId}`);
      alert("Collection retirée !");
      loadUserCollections(userId);
    } catch (error) {
      console.error(error);
      alert("Erreur lors de la suppression de la collection");
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header>
        <h2 className="text-3xl font-bold mb-2">Gestion des utilisateurs</h2>
        <p className="text-sm text-gray-600">
          Seul un <span className="font-semibold">superadmin</span> peut accéder à cette page.
        </p>
      </header>

      {/* --- Formulaire de création d'utilisateur --- */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Créer un nouvel utilisateur</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Username */}
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={newUserUsername}
              onChange={(e) => setNewUserUsername(e.target.value)}
              className="border rounded p-2 w-full"
              placeholder="ex: admin2"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              value={newUserPassword}
              onChange={(e) => setNewUserPassword(e.target.value)}
              className="border rounded p-2 w-full"
              placeholder="ex: secret123"
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium mb-1">Role</label>
            <select
              value={newUserRole}
              onChange={(e) => setNewUserRole(e.target.value as 'admin' | 'superadmin')}
              className="border p-2 w-full rounded"
            >
              <option value="admin">admin</option>
              <option value="superadmin">superadmin</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end mt-4">
          <button
            onClick={handleCreateUser}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-semibold rounded shadow hover:bg-blue-700 transition-colors"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4v16m8-8H4"
              />
            </svg>
            Créer
          </button>
        </div>
      </div>

      {/* --- Liste des utilisateurs --- */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Liste des utilisateurs</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border">
            <thead>
              <tr className="bg-gray-100 border-b">
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                  ID
                </th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                  Username
                </th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                  Role
                </th>
                <th className="px-4 py-2 text-right text-sm font-medium text-gray-700">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <React.Fragment key={u.id}>
                  <tr className="border-b">
                    <td className="px-4 py-2 text-sm text-gray-800">
                      {u.id}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-800">
                      {u.username}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-800">
                      {u.role}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {/* Supprimer l'utilisateur */}
                      <button
                        onClick={() => handleDeleteUser(u.id)}
                        className="inline-flex items-center bg-red-500 text-white text-sm px-3 py-1 rounded hover:bg-red-600 transition-colors mr-2"
                      >
                        <svg
                          className="w-4 h-4 mr-1"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 
                               4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 
                               1 0 00-1 1v3m-3 0h12"
                          />
                        </svg>
                        Supprimer
                      </button>

                      {/* Gérer les collections */}
                      <button
                        onClick={() => toggleUserCollections(u.id)}
                        className="inline-flex items-center bg-green-600 text-white text-sm px-3 py-1 rounded hover:bg-green-700 transition-colors"
                      >
                        <svg
                          className="w-4 h-4 mr-1"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                        Gérer Collections
                      </button>
                    </td>
                  </tr>

                  {/* Sous-ligne pour gérer les collections, si expanded */}
                  {expandedUserId === u.id && (
                    <tr>
                      <td colSpan={4} className="p-4 bg-gray-50">
                        <div className="space-y-4">
                          <h4 className="font-semibold">Collections de {u.username}</h4>
                          
                          {/* Collections déjà attribuées */}
                          <div>
                            <p className="text-sm text-gray-700 mb-2">Collections assignées :</p>
                            {userCollections[u.id] && userCollections[u.id].length > 0 ? (
                              <ul className="list-disc list-inside space-y-1">
                                {userCollections[u.id].map((coll) => (
                                  <li key={coll.id} className="flex items-center justify-between">
                                    <span>{coll.name}</span>
                                    <button
                                      onClick={() => handleUnassignCollection(u.id, coll.id)}
                                      className="inline-flex items-center bg-red-400 text-white text-xs px-2 py-1 rounded hover:bg-red-500"
                                    >
                                      Retirer
                                    </button>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-sm text-gray-500">Aucune collection.</p>
                            )}
                          </div>

                          {/* Assigner une collection */}
                          <div className="flex items-center gap-2">
                            <select
                              className="border p-1 rounded"
                              value={selectedCollectionToAssign[u.id] || ''}
                              onChange={(e) => {
                                const val = Number(e.target.value);
                                setSelectedCollectionToAssign(prev => ({
                                  ...prev,
                                  [u.id]: val
                                }));
                              }}
                            >
                              <option value="">-- Choisir une collection --</option>
                              {allCollections.map((coll) => {
                                // On masque celles déjà assignées
                                const alreadyAssigned = (userCollections[u.id] || []).some(c => c.id === coll.id);
                                if (alreadyAssigned) return null;
                                return (
                                  <option key={coll.id} value={coll.id}>
                                    {coll.name}
                                  </option>
                                );
                              })}
                            </select>
                            <button
                              onClick={() => handleAssignCollection(u.id)}
                              className="inline-flex items-center bg-blue-500 text-white text-sm px-3 py-1 rounded hover:bg-blue-600 transition-colors"
                            >
                              Assigner
                            </button>
                          </div>

                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-sm text-gray-500 py-4">
                    Aucun utilisateur pour l’instant.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
