import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Loader2, Send, Crosshair } from 'lucide-react';
import ImageUpload from '../components/ImageUpload';
import { useToast } from '../components/Toast';
import { submitReport, type Category } from '../services/api';
import MapLibreLocationPicker from '../components/MapLibreLocationPicker';

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
  const [locationLabel, setLocationLabel] = useState('');
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleLocationConfirm = (lat: number, lng: number) => {
    setLatitude(lat.toFixed(6));
    setLongitude(lng.toFixed(6));
    setLocationLabel('Location selected on map');
    setIsPickerOpen(false);
  };

  const validate = () => {
    const next: Record<string, string> = {};
    if (!image) next.image = 'A photograph is required.';
    if (description.trim().length < 10) next.description = 'Description must be at least 10 characters.';
    const lat = Number(latitude);
    const lng = Number(longitude);
    if (latitude === '' || Number.isNaN(lat) || lat < -90 || lat > 90) next.location = 'Please select a location on the map.';
    if (longitude === '' || Number.isNaN(lng) || lng < -180 || lng > 180) next.location = 'Please select a location on the map.';
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
      navigate('/reports/' + report.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to submit report.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className='max-w-3xl mx-auto px-6 py-12'>
      <h1 className='text-3xl font-bold text-white mb-2'>Report an Issue</h1>
      <p className='text-gray-400 mb-8'>Submit a photograph, location, and description of the infrastructure issue.</p>

      <form onSubmit={onSubmit} className='space-y-6'>
        <ImageUpload file={image} onChange={setImage} error={errors.image} />

        <div>
          <label htmlFor='description' className='block text-sm font-medium text-gray-300 mb-2'>Description</label>
          <textarea
            id='description'
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className='w-full rounded-lg bg-gray-900/60 border border-gray-700 px-3 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50'
            placeholder='Describe the issue clearly (min 10 characters)...'
          />
          <div className='flex justify-between mt-1'>
            {errors.description ? <p className='text-sm text-red-400'>{errors.description}</p> : <span />}
            <span className='text-xs text-gray-500'>{description.length}/5000</span>
          </div>
        </div>

        <div>
          <label htmlFor='category' className='block text-sm font-medium text-gray-300 mb-2'>Category</label>
          <select
            id='category'
            value={category}
            onChange={(e) => setCategory(e.target.value as Category)}
            className='w-full rounded-lg bg-gray-900/60 border border-gray-700 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50'
          >
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>

        <div>
          <div className='flex items-center justify-between mb-2'>
            <span className='text-sm font-medium text-gray-300'>Location</span>
            <button
              type='button'
              onClick={() => setIsPickerOpen(true)}
              className='inline-flex items-center gap-1.5 text-sm text-brand-400 hover:text-brand-300'
            >
              <Crosshair size={14} />
              {latitude && longitude ? 'Change location' : 'Select on map'}
            </button>
          </div>

          {latitude && longitude ? (
            <div className='flex items-center gap-2 px-4 py-3 bg-gray-900/60 border border-gray-700 rounded-lg text-sm'>
              <MapPin size={15} className='text-brand-400 shrink-0' />
              <span className='text-gray-200'>{locationLabel || 'Location selected'}</span>
              <button
                type='button'
                onClick={() => { setLatitude(''); setLongitude(''); setLocationLabel(''); }}
                className='ml-auto text-xs text-gray-500 hover:text-gray-300'
              >
                Clear
              </button>
            </div>
          ) : (
            <button
              type='button'
              onClick={() => setIsPickerOpen(true)}
              className='w-full flex items-center justify-center gap-2 px-4 py-6 bg-gray-900/60 border border-dashed border-gray-700 hover:border-gray-600 rounded-lg text-sm text-gray-400 hover:text-gray-300 transition-colors'
            >
              <MapPin size={18} />
              Click to select the issue location on a map
            </button>
          )}
          {errors.location && <p className='mt-1 text-sm text-red-400'>{errors.location}</p>}
        </div>

        <button
          type='submit'
          disabled={submitting}
          className='inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-400 text-white font-medium disabled:opacity-50 transition-colors'
        >
          {submitting ? <Loader2 size={18} className='animate-spin' /> : <Send size={18} />}
          {submitting ? 'Submitting...' : 'Submit Report'}
        </button>
      </form>

      <MapLibreLocationPicker
        isOpen={isPickerOpen}
        onClose={() => setIsPickerOpen(false)}
        onConfirm={handleLocationConfirm}
        initialLat={latitude ? parseFloat(latitude) : undefined}
        initialLng={longitude ? parseFloat(longitude) : undefined}
        autoLocateOnOpen={!latitude || !longitude}
      />
    </div>
  );
}
