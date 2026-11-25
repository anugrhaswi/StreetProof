import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { Upload, X, ImageIcon } from 'lucide-react';

const MAX_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ['image/jpeg', 'image/png'];

interface ImageUploadProps {
  file: File | null;
  onChange: (file: File | null) => void;
  error?: string;
}

export default function ImageUpload({ file, onChange, error }: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const validate = (f: File): string | null => {
    if (!ALLOWED_TYPES.includes(f.type)) return 'Only JPG, JPEG, and PNG images are allowed.';
    if (f.size > MAX_SIZE) return 'Image must be 5 MB or smaller.';
    return null;
  };

  const handleFile = (f: File | undefined) => {
    if (!f) return;
    const err = validate(f);
    if (err) {
      setLocalError(err);
      onChange(null);
      return;
    }
    setLocalError(null);
    onChange(f);
  };

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0]);
    e.target.value = '';
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const preview = file ? URL.createObjectURL(file) : null;
  const displayError = error || localError;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">Photograph</label>
      {!file ? (
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragOver ? 'border-brand-400 bg-brand-500/5' : 'border-gray-700 hover:border-gray-600 bg-gray-900/20'
          }`}
        >
          <Upload className="mx-auto mb-3 text-gray-400" size={28} />
          <p className="text-sm text-gray-300">Drop an image here, or click to select</p>
          <p className="text-xs text-gray-500 mt-1">JPG, JPEG, PNG &middot; Max 5 MB</p>
        </div>
      ) : (
        <div className="relative inline-block">
          <img
            src={preview!}
            alt="Selected upload preview"
            className="w-[200px] h-[150px] object-cover rounded-lg border border-gray-700"
            onLoad={() => preview && URL.revokeObjectURL(preview)}
          />
          <button
            type="button"
            onClick={() => { setLocalError(null); onChange(null); }}
            className="absolute -top-2 -right-2 p-1 rounded-full bg-gray-800 border border-gray-600 text-gray-300 hover:text-white"
            aria-label="Remove image"
          >
            <X size={14} />
          </button>
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
            <ImageIcon size={14} />
            <span className="truncate max-w-[180px]">{file.name}</span>
          </div>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,.jpg,.jpeg,.png"
        className="hidden"
        onChange={onInputChange}
      />
      {displayError && <p className="mt-2 text-sm text-red-400">{displayError}</p>}
    </div>
  );
}
