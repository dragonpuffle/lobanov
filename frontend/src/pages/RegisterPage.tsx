import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useRegister } from '@/features/auth/api/useAuthMutations'
import { PasswordStrength, usePasswordScore } from '@/features/auth/ui/PasswordStrength'
import { motion } from 'framer-motion'
import { FileText } from 'lucide-react'

const strong = (pwd: string) => {
  const p = [pwd.length >= 8, /[A-Z]/.test(pwd), /[a-z]/.test(pwd), /[0-9]/.test(pwd), /[^A-Za-z0-9]/.test(pwd)].filter(
    Boolean,
  ).length
  return p === 5
}

const schema = z
  .object({
    email: z.string().email(),
    full_name: z.string().min(2),
    password: z.string().min(8).refine(strong, { message: 'weak' }),
    password2: z.string(),
  })
  .refine((d) => d.password === d.password2, { path: ['password2'] })

type Form = z.infer<typeof schema>

export function RegisterPage() {
  const { t } = useTranslation()
  const reg = useRegister()
  const f = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { full_name: '', email: '', password: '', password2: '' } })
  const pwd = f.watch('password')
  const { passed } = usePasswordScore(pwd ?? '')

  return (
    <div className="from-background to-muted/30 flex min-h-dvh items-center justify-center bg-gradient-to-br p-4">
      <div className="grid w-full max-w-4xl gap-8 lg:grid-cols-2 lg:items-center">
        <motion.div
          className="hidden space-y-4 lg:block"
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <FileText className="text-primary size-12" />
          <h1 className="text-3xl font-bold tracking-tight">{t('app.name')}</h1>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="border-border/80 shadow-lg">
            <CardHeader>
              <CardTitle>{t('auth.register')}</CardTitle>
              <CardDescription>Create a doctor account. Then log in to receive a JWT.</CardDescription>
            </CardHeader>
            <form
              onSubmit={f.handleSubmit((data) => {
                reg.mutate({ email: data.email, password: data.password, full_name: data.full_name })
              })}
            >
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="fn">{t('auth.fullName')}</Label>
                  <Input id="fn" {...f.register('full_name')} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="em">{t('auth.email')}</Label>
                  <Input id="em" type="email" {...f.register('email')} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pw">{t('auth.password')}</Label>
                  <Input id="pw" type="password" {...f.register('password')} />
                  <PasswordStrength password={pwd ?? ''} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pw2">{t('auth.password')}</Label>
                  <Input id="pw2" type="password" {...f.register('password2')} />
                </div>
                {f.formState.errors.password2 ? <p className="text-destructive text-sm">Passwords must match</p> : null}
              </CardContent>
              <CardFooter className="flex flex-col gap-2">
                <Button type="submit" className="w-full" disabled={reg.isPending || passed < 5}>
                  {t('auth.register')}
                </Button>
                <p className="text-muted-foreground text-center text-sm">
                  <Link to="/login" className="text-primary underline">
                    {t('auth.login')}
                  </Link>
                </p>
              </CardFooter>
            </form>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
