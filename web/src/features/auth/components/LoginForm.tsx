import { useNavigate } from 'react-router-dom';
import { useLogin } from '@/features/auth/hooks';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginForm() {
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });
  const loginMutation = useLogin();

  const onSubmit = (data: LoginFormData) => {
    loginMutation.mutate(data);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8">
        <div>
          <div className="flex items-center gap-2 justify-center mb-2">
            <img src="/favicon.svg" alt="MwalimuKit" className="h-8 w-8" />
            <span className="text-2xl font-bold text-gray-900">MwalimuKit</span>
          </div>
          <h1 className="text-center text-gray-600">Sign in to your account</h1>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              {...register('email')}
              type="email"
              autoComplete="email"
              className={`input ${errors.email ? 'border-red-500' : ''}`}
              placeholder="you@school.example"
            />
            {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
          </div>

          <div>
            <label className="label">Password</label>
            <input
              {...register('password')}
              type="password"
              autoComplete="current-password"
              className={`input ${errors.password ? 'border-red-500' : ''}`}
              placeholder="Password"
            />
            {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || loginMutation.isPending}
            className="btn-primary w-full"
          >
            {isSubmitting || loginMutation.isPending ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={() => navigate('/signup')}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            Sign up
          </button>
        </div>
      </div>
    </div>
  );
}
