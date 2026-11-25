import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Loader2, Send } from 'lucide-react';
import ImageUpload from '../components/ImageUpload';
import { useToast } from '../components/Toast';
import { submitReport, type Category } from '../services/api';

const CATEGORIES: { value: Category; label: string }[] = [
  { value: 'pothole', label: 'Pothole' },
  { value: 'streetlight', label: 'Streetlight' },
  { value: 'garbage', label: 'Garbage' },
  { value: 'graffiti', label: 'Graffiti' },
  { value: 'sidewalk', label: 'Sidewalk' },
  { value: 'signage', label: 'Signage' },
  { value: 'drainage', label: 'Drainage' },
  { value: 'other', label: 'Other' },
];

export default function Report() {
  const navigate = useNavigate();
  const toast = useToast();
  const [image, setImage] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<Category>('pothole');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation is not supported by your browser.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        setLocating(false);
        toast.success('Location captured. You can adjust it manually if needed.');
      },
      (err) => {
        setLocating(false);
        if (err.code === err.PERMISSION_DENIED) toast.error('Location permission denied.');
        else toast.error('Unable to retrieve your location.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const validate = () => {
    const next: Record<string, string> = {};
    if (!image) next.image = 'A photograph is required.';
    if (description.trim().length < 10) next.description = 'Description must be at least 10 characters.';
    const lat = Number(latitude);
    const lng = Number(longitude);
    if (latitude === '' || Number.isNaN(lat) || lat < -90 || lat > 90) next.latitude = 'Latitude must be between -90 and 90.';
    if (longitude === '' || Number.isNaN(lng) || lng < -180 || lng > 180) next.longitude = 'Longitude must be between -180 and 180.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate() || !image) return;
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('description', description.trim());
      fd.append('category', category);
      fd.append('latitude', latitude);
      fd.append('longitude', longitude);
      fd.append('image', image);
      const report = await submitReport(fd);
      toast.success('Report submitted successfully.');
      navigate(`/reports/${report.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to submit report.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold text-white mb-2">Report an Issue</h1>
      <p className="text-gray-400 mb-8">Submit a photograph, location, and description of the infrastructure issue.</p>

      <form onSubmit={onSubmit} className="space-y-6">
        <ImageUpload file={image} onChange={setImage} error={errors.image} />

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-300 mb-2">Description</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full rounded-lg bg-gray-900/60 border border-gray-700 px-3 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
            placeholder="Describe the issue clearly (min 10 characters)..."
          />
          <div className="flex justify-between mt-1">
            {errors.description ? <p className="text-sm text-red-400">{errors.description}</p> : <span />}
            <span className="text-xs text-gray-500">{description.length}/5000</span>
          </div>
        </div>

        <div>
          <label htmlFor="category" className="block text-sm font-medium text-gray-300 mb-2">Category</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value as Category)}
            className="w-full rounded-lg bg-gray-900/60 border border-gray-700 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
          >
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">Coordinates</span>
            <button
              type="button"
              onClick={useMyLocation}
              disabled={locating}
              className="inline-flex items-center gap-1.5 text-sm text-brand-400 hover:text-brand-300 disabled:opacity-50"
            >
              {locating ? <Loader2 size={14} className="animate-spin" /> : <MapPin size={14} />}
              Use my location
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="latitude" className="block text-xs text-gray-400 mb-1">Latitude</label>
              <input
                id="latitude"
                type="number"
                step="0.000001"
                min={-90}
                max={90}
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                className="w-full rounded-lg bg-gray-900/60 border border-gray-700 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                placeholder="-90 to 90"
              />
              {errors.latitude && <p className="mt-1 text-sm text-red-400">{errors.latitude}</p>}
            </div>
            <div>
              <label htmlFor="longitude" className="block text-xs text-gray-400 mb-1">Longitude</label>
              <input
                id="longitude"
                type="number"
                step="0.000001"
                min={-180}
                max={180}
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                className="w-full rounded-lg bg-gray-900/60 border border-gray-700 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                placeholder="-180 to 180"
              />
              {errors.longitude && <p className="mt-1 text-sm text-red-400">{errors.longitude}</p>}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-400 text-white font-medium disabled:opacity-50 transition-colors"
        >
          {submitting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          {submitting ? 'Submitting...' : 'Submit Report'}
        </button>
      </form>
    </div>
  );
}
