import { useNavigate } from 'react-router-dom';
import { useSignup } from '@/features/auth/hooks';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const signupSchema = z.object({
  full_name: z.string().min(2, 'Full name is required'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  school_code: z.string().min(4, 'School code is required'),
});

type SignupFormData = z.infer<typeof signupSchema>;

export function SignupForm() {
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
  });
  const signupMutation = useSignup();

  const onSubmit = (data: SignupFormData) => {
    signupMutation.mutate(data);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8">
        <div>
          <div className="flex items-center gap-2 justify-center mb-2">
            <img src="/favicon.svg" alt="MwalimuKit" className="h-8 w-8" />
            <span className="text-2xl font-bold text-gray-900">MwalimuKit</span>
          </div>
          <h1 className="text-center text-gray-600">Create your account</h1>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Full Name</label>
            <input
              {...register('full_name')}
              type="text"
              autoComplete="name"
              className={`input ${errors.full_name ? 'border-red-500' : ''}`}
              placeholder="Jane Teacher"
            />
            {errors.full_name && <p className="text-xs text-red-600">{errors.full_name.message}</p>}
          </div>

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
              autoComplete="new-password"
              className={`input ${errors.password ? 'border-red-500' : ''}`}
              placeholder="Min 8 characters"
            />
            {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
          </div>

          <div>
            <label className="label">School Code</label>
            <input
              {...register('school_code')}
              type="text"
              autoComplete="one-time-code"
              className={`input ${errors.school_code ? 'border-red-500' : ''}`}
              placeholder="e.g. DEMO01"
            />
            {errors.school_code && <p className="text-xs text-red-600">{errors.school_code.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || signupMutation.isPending}
            className="btn-primary w-full"
          >
            {isSubmitting || signupMutation.isPending ? 'Creating...' : 'Sign Up'}
          </button>
        </form>

        <div className="text-center text-sm text-gray-600">
          Already have an account?{' '}
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
}
