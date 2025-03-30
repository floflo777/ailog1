import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import 'katex/dist/katex.min.css';
import api from '../api/axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  context?: string[];
}

interface CollectionItem {
  id: number;
  name: string;
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [useRAG, setUseRAG] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api.get('/admin/my-collections')
      .then(res => {
        if (res.data && res.data.collections) {
          setCollections(res.data.collections);
          if (res.data.collections.length > 0) {
            setSelectedCollectionId(res.data.collections[0].id);
          }
        }
      })
      .catch(e => {
        console.error(e);
        setError("Impossible de charger la liste des collections pour le chat.");
      });
  }, []);

  const markdownComponents = {
    p: ({ children, ...props }: React.HTMLProps<HTMLParagraphElement>) => (
      <p className="mb-4 text-gray-800" {...props}>{children}</p>
    ),
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    if (!selectedCollectionId && useRAG) {
      setError("Veuillez choisir une collection pour le RAG");
      return;
    }

    setIsLoading(true);
    setError('');

    const newMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, newMessage]);
    setInput('');

    try {
      let url = '/chat';
      if (useRAG && selectedCollectionId) {
        url += `?collection_id=${selectedCollectionId}`;
      } else {
        url += `?collection_id=${selectedCollectionId || 1}`;
      }

      const response = await api.post(url, {
        message: input,
        useRAG: useRAG,
        history: messages
      });

      if (response.data) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.data.response,
          context: response.data.context
        }]);
      }
    } catch (error) {
      console.error('Error details:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Désolé, une erreur s'est produite lors de la communication avec le serveur."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Chat</h2>
        <div className="flex items-center space-x-2">
          <label className="text-sm">RAG</label>
          <div
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
              useRAG ? 'bg-indigo-600' : 'bg-gray-200'
            }`}
            onClick={() => setUseRAG(!useRAG)}
            role="switch"
            aria-checked={useRAG}
            tabIndex={0}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                useRAG ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Sélecteur de collection si useRAG */}
      {useRAG && collections.length > 0 && (
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Choix de la Collection</label>
          <select
            className="border rounded p-2 w-full"
            value={selectedCollectionId || ''}
            onChange={(e) => setSelectedCollectionId(Number(e.target.value))}
          >
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <p className="text-red-500 mb-2">{error}</p>}

      <div className="bg-white rounded-lg shadow mb-4 p-6">
        <div 
          className="space-y-6 h-[60vh] overflow-y-auto"
          style={{ scrollBehavior: 'smooth' }}
        >
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[90%] ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white rounded-l-lg rounded-br-lg'
                    : 'bg-gray-100 text-gray-900 rounded-r-lg rounded-bl-lg'
                } p-4`}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkMath, remarkGfm]}
                  rehypePlugins={[rehypeKatex]}
                  className="prose max-w-none dark:prose-invert"
                  components={markdownComponents}
                >
                  {message.content}
                </ReactMarkdown>
                {message.context && message.context.length > 0 && (
                  <div className="text-xs mt-2 text-gray-400">
                    Sources: {message.context.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Posez votre question..."
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50 hover:bg-blue-600 transition-colors"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
};

export default ChatPage;
