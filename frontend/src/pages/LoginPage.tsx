import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useLogin } from '@/features/auth/api/useAuthMutations'
import { motion } from 'framer-motion'
import { FileText } from 'lucide-react'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

type Form = z.infer<typeof schema>

export function LoginPage() {
  const { t } = useTranslation()
  const login = useLogin()
  const f = useForm<Form>({ resolver: zodResolver(schema) })

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
          <p className="text-muted-foreground text-lg">Semi-automated medical documentation from audio & NLP.</p>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="border-border/80 shadow-lg">
            <CardHeader>
              <CardTitle>{t('auth.login')}</CardTitle>
              <CardDescription>JWT access to the Medical Documentation API.</CardDescription>
            </CardHeader>
            <form
              onSubmit={f.handleSubmit((data) => {
                login.mutate(data)
              })}
            >
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">{t('auth.email')}</Label>
                  <Input id="email" type="email" autoComplete="email" {...f.register('email')} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">{t('auth.password')}</Label>
                  <Input id="password" type="password" autoComplete="current-password" {...f.register('password')} />
                </div>
              </CardContent>
              <CardFooter className="flex flex-col gap-2">
                <Button type="submit" className="w-full" disabled={login.isPending}>
                  {t('auth.login')}
                </Button>
                <p className="text-muted-foreground text-center text-sm">
                  <Link to="/register" className="text-primary underline">
                    {t('auth.register')}
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
