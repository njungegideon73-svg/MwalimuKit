import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/lib/auth-store';
import toast from 'react-hot-toast';
import { CloudOff } from 'lucide-react';

const schema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  school_code: z.string().min(4, 'School code is required'),
});

type FormData = z.infer<typeof schema>;

export function SignupPage() {
  const signup = useAuthStore((s) => s.signup);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await signup(data);
      navigate('/');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Signup failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 bg-gray-50">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-primary-500 mb-4">
            <span className="text-white font-bold text-xl">MK</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
          <p className="text-gray-500 mt-1">Join MwalimuKit as a teacher</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4">
          {!isOnline && (
            <div className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              <CloudOff className="h-4 w-4 shrink-0" />
              Sign-up needs internet the first time. After that, everything works offline.
            </div>
          )}
          <div>
            <label className="label">Full name</label>
            <input {...register('full_name')} className="input" placeholder="Grace Muthoni" />
            {errors.full_name && <p className="mt-1 text-sm text-red-600">{errors.full_name.message}</p>}
          </div>
          <div>
            <label className="label">Email</label>
            <input {...register('email')} type="email" className="input" placeholder="you@school.ac.ke" />
            {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
          </div>
          <div>
            <label className="label">Password</label>
            <input {...register('password')} type="password" className="input" placeholder="Min. 8 characters" />
            {errors.password && <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>}
          </div>
          <div>
            <label className="label">School code</label>
            <input {...register('school_code')} className="input" placeholder="DEMO01" />
            {errors.school_code && (
              <p className="mt-1 text-sm text-red-600">{errors.school_code.message}</p>
            )}
            <p className="mt-1 text-xs text-gray-400">
              Ask your school admin for the join code.
            </p>
          </div>
          <button type="submit" disabled={loading || !isOnline} className="btn-primary w-full">
            {loading ? 'Creating account...' : !isOnline ? 'Offline — connect to sign up' : 'Create account'}
          </button>
          <p className="text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
