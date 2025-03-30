import React, { useEffect, useState } from 'react';
import api from '../api/axios';

interface RAGSettings {
  chunk_size: number;
  chunk_overlap: number;
  temperature: number;
  similarity_threshold: number;
  rag_limit: number;
  model_name: string;
  top_p: number;
  presence_penalty: number;
  frequency_penalty: number;
  max_tokens: number;
  system_message: string;
  expressions: string; 
}

const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<RAGSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/settings')
      .then((res) => {
        setSettings(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError('Erreur lors du chargement des paramètres');
        setLoading(false);
      });
  }, []);

  const handleUpdate = () => {
    if (!settings) return;

    api.post('/settings', settings)
      .then((res) => {
        setSettings(res.data);
        alert('Paramètres mis à jour avec succès!');
      })
      .catch(() => {
        setError('Erreur lors de la mise à jour des paramètres');
      });
  };

  const handleChange = (key: keyof RAGSettings, value: string | number) => {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  };

  if (loading) {
    return <div className="p-6">Chargement en cours...</div>;
  }
  if (error) {
    return <div className="p-6 text-red-500">{error}</div>;
  }
  if (!settings) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-8">
      <header className="mb-4">
        <h2 className="text-3xl font-bold">Paramètres RAG</h2>
        <p className="text-sm text-gray-600">
          Ajustez la configuration de la recherche et de la génération.  
          Les modifications sont globales et affectent tous les utilisateurs.
        </p>
      </header>

      {/* --- SECTION 1 : Paramètres Chunks / Overlap --- */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Segmentation du texte</h3>
        <p className="text-sm text-gray-500 mb-6">
          Contrôle la façon dont les documents sont découpés en “chunks” pour l’indexation et la génération de Q&A.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Chunk Size */}
          <div>
            <label className="block font-medium mb-1">
              Chunk Size 
              <span className="text-xs text-gray-400 ml-1">
                (nombre de tokens par chunk)
              </span>
            </label>
            <input
              type="number"
              value={settings.chunk_size}
              onChange={(e) => handleChange('chunk_size', parseInt(e.target.value, 10))}
              className="border rounded p-2 w-full"
              min={1}
            />
          </div>

          {/* Chunk Overlap */}
          <div>
            <label className="block font-medium mb-1">
              Chunk Overlap 
              <span className="text-xs text-gray-400 ml-1">
                (chevauchement en tokens)
              </span>
            </label>
            <input
              type="number"
              value={settings.chunk_overlap}
              onChange={(e) => handleChange('chunk_overlap', parseInt(e.target.value, 10))}
              className="border rounded p-2 w-full"
              min={0}
            />
          </div>
        </div>
      </div>

      {/* --- SECTION 2 : Paramètres d'Embedding / Recherche --- */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Recherche &amp; Similarité</h3>
        <p className="text-sm text-gray-500 mb-6">
          Règle la sensibilité de la recherche vectorielle et le modèle utilisé.
        </p>
        <div className="space-y-4">
          {/* Model Name */}
          <div>
            <label className="block font-medium mb-1">
              Modèle 
              <span className="text-xs text-gray-400 ml-1">(ex: gpt-4, gpt-3.5-turbo)</span>
            </label>
            <input
              type="text"
              value={settings.model_name}
              onChange={(e) => handleChange('model_name', e.target.value)}
              className="border rounded p-2 w-full"
            />
          </div>

          {/* Similarity Threshold */}
          <div>
            <label className="block font-medium mb-1">
              Similarity Threshold
              <span className="text-xs text-gray-400 ml-1">(filtrage en recherche)</span>
            </label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={settings.similarity_threshold}
                onChange={(e) => handleChange('similarity_threshold', parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="w-12 text-right text-sm font-semibold">
                {settings.similarity_threshold.toFixed(2)}
              </span>
            </div>
          </div>

          {/* RAG Limit */}
          <div>
            <label className="block font-medium mb-1">
              Nombre max de chunks
              <span className="text-xs text-gray-400 ml-1">(limite RAG)</span>
            </label>
            <input
              type="number"
              value={settings.rag_limit}
              onChange={(e) => handleChange('rag_limit', parseInt(e.target.value, 10))}
              className="border rounded p-2 w-full"
              min={1}
            />
          </div>
        </div>
      </div>

      {/* --- SECTION 3 : Paramètres Génération (Temperature, etc.) --- */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Génération GPT</h3>
        <p className="text-sm text-gray-500 mb-6">
          Paramètres influençant la créativité et la tonalité de la réponse.
        </p>
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Temperature */}
            <div>
              <label className="block font-medium mb-1">
                Temperature
                <span className="text-xs text-gray-400 ml-1">(0-2)</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={settings.temperature}
                onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
                className="border rounded p-2 w-full"
              />
            </div>
            {/* top_p */}
            <div>
              <label className="block font-medium mb-1">
                top_p
                <span className="text-xs text-gray-400 ml-1">(0-1 nucleus sampling)</span>
              </label>
              <div className="flex items-center space-x-3">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={settings.top_p}
                  onChange={(e) => handleChange('top_p', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="w-12 text-right text-sm font-semibold">
                  {settings.top_p.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* presence_penalty */}
            <div>
              <label className="block font-medium mb-1">
                Presence Penalty
                <span className="text-xs text-gray-400 ml-1">(0-2)</span>
              </label>
              <div className="flex items-center space-x-3">
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={settings.presence_penalty}
                  onChange={(e) => handleChange('presence_penalty', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="w-10 text-right text-sm font-semibold">
                  {settings.presence_penalty.toFixed(1)}
                </span>
              </div>
            </div>
            {/* frequency_penalty */}
            <div>
              <label className="block font-medium mb-1">
                Frequency Penalty
                <span className="text-xs text-gray-400 ml-1">(0-2)</span>
              </label>
              <div className="flex items-center space-x-3">
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={settings.frequency_penalty}
                  onChange={(e) => handleChange('frequency_penalty', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="w-10 text-right text-sm font-semibold">
                  {settings.frequency_penalty.toFixed(1)}
                </span>
              </div>
            </div>
            {/* max_tokens */}
            <div>
              <label className="block font-medium mb-1">
                Max Tokens
                <span className="text-xs text-gray-400 ml-1">(limite GPT)</span>
              </label>
              <input
                type="number"
                value={settings.max_tokens}
                onChange={(e) => handleChange('max_tokens', parseInt(e.target.value, 10))}
                className="border rounded p-2 w-full"
                min={1}
              />
            </div>
          </div>

          {/* system_message */}
          <div>
            <label className="block font-medium mb-1">
              System Message
              <span className="text-xs text-gray-400 ml-1">(contexte global GPT)</span>
            </label>
            <textarea
              value={settings.system_message}
              onChange={(e) => handleChange('system_message', e.target.value)}
              className="border rounded p-2 w-full min-h-[80px]"
            />
            <p className="text-xs text-gray-500 mt-1">
              Laissez vide pour utiliser le message système par défaut.
            </p>
          </div>
        </div>
      </div>

      {/* --- SECTION : Expressions Anonymisées --- */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Expressions Anonymisées</h3>
        <p className="text-sm text-gray-500 mb-4">
          Liste brute des expressions séparées par ";".  
          Vous pouvez la modifier ou la compléter ici.
        </p>
        <textarea
          value={settings.expressions || ''}
          onChange={(e) => handleChange('expressions', e.target.value)}
          className="border rounded p-2 w-full min-h-[100px]"
        />
      </div>

      {/* --- BOUTON D'ENREGISTREMENT --- */}
      <div className="flex justify-end">
        <button
          onClick={handleUpdate}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-semibold rounded-md shadow hover:bg-blue-700 transition-colors"
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
              d="M5 12l4 4L19 7"
            />
          </svg>
          Enregistrer
        </button>
      </div>
    </div>
  );
};

export default SettingsPage;
