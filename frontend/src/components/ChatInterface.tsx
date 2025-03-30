import React, { useState, ChangeEvent, FormEvent, useEffect } from 'react';
import api from '../api/axios';
import ReactMarkdown from 'react-markdown';
import { PlusCircle, Trash2, Save } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";

interface QAPair {
  question: string;
  answer: string;
}

interface CollectionItem {
  id: number;
  name: string;
}

const ChatInterface: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [responses, setResponses] = useState<QAPair[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDirectoryMode, setIsDirectoryMode] = useState(false);
  const [directoryFiles, setDirectoryFiles] = useState<FileList | null>(null);
  const [processedFiles, setProcessedFiles] = useState<string[]>([]);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);

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
      .catch(err => {
        console.error(err);
        setError("Impossible de charger la liste des collections");
      });
  }, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    if (isDirectoryMode) {
      setDirectoryFiles(files);
      setProcessedFiles([]);
      setProcessingProgress(0);
    } else {
      const selectedFile = files[0];
      const allowedTypes = [
        'application/pdf',
        'text/plain',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ];
      
      if (allowedTypes.includes(selectedFile.type)) {
        setFile(selectedFile);
        setError('');
      } else {
        setError('Type de fichier non supporté. Veuillez utiliser PDF, TXT, DOC, DOCX, XLS ou XLSX.');
      }
    }
  };

  const handleQuestionChange = (index: number, value: string) => {
    const newResponses = [...responses];
    newResponses[index].question = value;
    setResponses(newResponses);
  };

  const handleAnswerChange = (index: number, value: string) => {
    const newResponses = [...responses];
    newResponses[index].answer = value;
    setResponses(newResponses);
  };

  const addNewQA = () => {
    setResponses([...responses, { question: '', answer: '' }]);
  };

  const removeQA = (index: number) => {
    const newResponses = responses.filter((_, i) => i !== index);
    setResponses(newResponses);
  };

  const handleSingleFileSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Veuillez sélectionner un fichier');
      return;
    }
    if (!selectedCollectionId) {
      setError('Veuillez choisir une collection');
      return;
    }

    setIsLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_id', String(selectedCollectionId));

    try {
      const result = await api.post('/documents/process-document', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });

      setResponses(result.data.qa_pairs);
    } catch (error) {
      setError('Erreur lors du traitement du document');
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDirectorySubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!directoryFiles) {
      return;
    }
    if (!selectedCollectionId) {
      setError('Veuillez choisir une collection');
      return;
    }

    setIsLoading(true);
    setError('');
    setProcessedFiles([]);
    setResponses([]);

    const formData = new FormData();
    Array.from(directoryFiles).forEach(file => {
      formData.append('files', file);
    });
    formData.append('collection_id', String(selectedCollectionId));

    try {
      const result = await api.post('/documents/process-directory', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = (progressEvent.loaded / progressEvent.total) * 100;
            setProcessingProgress(progress);
          }
        },
      });

      setResponses(result.data.qa_pairs);
      setProcessedFiles(result.data.processed_files);
    } catch (error) {
      setError('Erreur lors du traitement du dossier');
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
      setProcessingProgress(0);
    }
  };

  const handleSaveToQdrant = async () => {
    if (!file) return;
    if (!selectedCollectionId) {
      alert("Veuillez choisir une collection");
      return;
    }
    
    try {
      setIsLoading(true);

      const formData = new FormData();
      formData.append('file', file);

      const analysisObject = {
        qa_pairs: responses
      };
      formData.append('document_analysis', JSON.stringify(analysisObject));
      formData.append('collection_id', String(selectedCollectionId)); 

      await api.post('/documents/save-to-qdrant', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });

      alert('Document et Q&A sauvegardés avec succès dans Qdrant!');
      setIsEditing(false);
    } catch (error) {
      setError('Erreur lors de la sauvegarde dans Qdrant');
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* En-tête avec toggle pour le mode dossier */}
      <div className="mb-6 p-4 bg-white rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Analyser des Documents</h2>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Mode dossier</span>
            <button
              type="button"
              onClick={() => {
                setIsDirectoryMode(!isDirectoryMode);
                setFile(null);
                setDirectoryFiles(null);
                setResponses([]);
                setProcessedFiles([]);
                setError('');
              }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                isDirectoryMode ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isDirectoryMode ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Sélecteur de collection */}
        {collections.length > 0 && (
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

        {/* Formulaire */}
        <form onSubmit={isDirectoryMode ? handleDirectorySubmit : handleSingleFileSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {isDirectoryMode ? 'Sélectionner des fichiers' : 'Document à analyser'}
            </label>
            <input
              type="file"
              onChange={handleFileChange}
              {...(isDirectoryMode ? { multiple: true } : {})}
              accept=".pdf,.txt,.doc,.docx,.xls,.xlsx"
              className="w-full p-2 border border-gray-300 rounded"
            />
          </div>

          {directoryFiles && isDirectoryMode && (
            <div className="text-sm text-gray-600">
              {directoryFiles.length} fichiers sélectionnés
            </div>
          )}

          {processingProgress > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${processingProgress}%` }}
              />
            </div>
          )}

          {error && <p className="text-red-500 mt-2">{error}</p>}

          <button
            type="submit"
            disabled={isLoading || (!file && !directoryFiles) || !selectedCollectionId}
            className="w-full px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50 hover:bg-blue-600"
          >
            {isLoading ? 'Traitement en cours...' : isDirectoryMode ? 'Analyser les fichiers' : 'Analyser le document'}
          </button>
        </form>
      </div>

      {/* Liste des fichiers traités */}
      {processedFiles.length > 0 && (
        <div className="mb-6 p-4 bg-white rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Fichiers traités</h3>
          <ul className="space-y-2">
            {processedFiles.map((file, index) => (
              <li key={index} className="flex items-center text-sm">
                <span className="mr-2 text-green-500">✓</span>
                {file}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Affichage des Q&A */}
      {responses.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold">Questions & Réponses</h3>
            <div className="space-x-4">
              {!isDirectoryMode && (
                <>
                  <Button
                    onClick={() => setIsEditing(!isEditing)}
                    variant="outline"
                  >
                    {isEditing ? 'Annuler l\'édition' : 'Éditer'}
                  </Button>
                  {isEditing && (
                    <Button
                      onClick={addNewQA}
                      variant="outline"
                      className="flex items-center gap-2"
                    >
                      <PlusCircle className="w-4 h-4" />
                      Ajouter Q&R
                    </Button>
                  )}
                  <Button
                    onClick={handleSaveToQdrant}
                    disabled={isLoading}
                    className="flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    Sauvegarder dans Qdrant
                  </Button>
                </>
              )}
            </div>
          </div>
          
          <div className="space-y-6">
            {responses.map((qa, index) => (
              <Card key={index} className="p-4">
                {isEditing ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Question {index + 1}
                      </label>
                      <div className="flex gap-4">
                        <Input
                          value={qa.question}
                          onChange={(e) => handleQuestionChange(index, e.target.value)}
                          placeholder="Entrez la question"
                          className="flex-1"
                        />
                        <Button
                          variant="destructive"
                          size="icon"
                          onClick={() => removeQA(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Réponse
                      </label>
                      <Textarea
                        value={qa.answer}
                        onChange={(e) => handleAnswerChange(index, e.target.value)}
                        placeholder="Entrez la réponse"
                        className="min-h-[100px]"
                      />
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="bg-blue-50 p-4 rounded-lg mb-4">
                      <p className="font-medium text-blue-800">Q: {qa.question}</p>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <ReactMarkdown
                        className="prose max-w-none"
                        components={{
                          p: ({...props}) => <p className="text-gray-700 mb-2" {...props} />,
                          ul: ({...props}) => <ul className="list-disc pl-4 mb-2" {...props} />,
                          ol: ({...props}) => <ol className="list-decimal pl-4 mb-2" {...props} />,
                          li: ({...props}) => <li className="text-gray-700 mb-1" {...props} />
                        }}
                      >
                        {`R: ${qa.answer}`}
                      </ReactMarkdown>
                    </div>
                  </>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
