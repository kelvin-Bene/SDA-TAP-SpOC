import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  User,
  Building2,
  Key,
  Shield,
  Copy,
  RefreshCw,
  Check,
  Eye,
  EyeOff,
  Loader2,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useLeaderboardStatistics } from '@/hooks/useLeaderboard';
import { useSubmissions } from '@/hooks/useSubmissions';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/api/client';

export function ProfilePage() {
  const { toast } = useToast();
  const { user } = useAuthStore();
  const [showApiKey, setShowApiKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Editable fields initialized from auth user data
  const [displayName, setDisplayName] = useState(user?.username ?? '');
  const [organization, setOrganization] = useState(user?.organization ?? '');
  const [udlToken, setUdlToken] = useState('');
  const [esaToken, setEsaToken] = useState('');
  const [showUdlToken, setShowUdlToken] = useState(false);
  const [showEsaToken, setShowEsaToken] = useState(false);
  const [udlTokenMask, setUdlTokenMask] = useState('');
  const [esaTokenMask, setEsaTokenMask] = useState('');

  // Fetch profile from backend to get masked token values
  useEffect(() => {
    api.getCurrentUser().then((res) => {
      const profile = res.data;
      if (profile.udl_token) setUdlTokenMask(profile.udl_token);
      if (profile.esa_token) setEsaTokenMask(profile.esa_token);
    }).catch(() => {
      // Ignore -- profile may not exist yet
    });
  }, []);

  // Fetch real stats from API
  const { data: stats } = useLeaderboardStatistics();
  const { data: submissions = [] } = useSubmissions();

  // Calculate user stats from real data
  const totalSubmissions = submissions.length;

  const placeholderApiKey = 'sk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx';

  const handleCopyApiKey = () => {
    navigator.clipboard.writeText(placeholderApiKey);
    setCopiedKey(true);
    toast({
      title: 'API Key Copied',
      description: 'Your API key has been copied to the clipboard.',
    });
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleRegenerateKey = () => {
    toast({
      title: 'API Key Regenerated',
      description: 'Your new API key has been generated. Update your applications.',
      variant: 'destructive',
    });
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const payload: Record<string, string> = {
        display_name: displayName,
        organization,
      };
      // Only send tokens when the user has typed a new value
      if (udlToken) payload.udl_token = udlToken;
      if (esaToken) payload.esa_token = esaToken;

      const res = await api.updateProfile(payload);
      const profile = res.data;

      // Update masks from response and clear raw inputs
      if (profile.udl_token) setUdlTokenMask(profile.udl_token);
      if (profile.esa_token) setEsaTokenMask(profile.esa_token);
      setUdlToken('');
      setEsaToken('');

      toast({
        title: 'Profile Updated',
        description: 'Your profile information has been saved.',
      });
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast({
        title: 'Update Failed',
        description: 'Failed to save profile changes. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Format member since date from user data
  const memberSince = user?.createdAt
    ? new Date(user.createdAt).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : '--';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-stellar-purple/20 to-cosmic-blue/20 flex items-center justify-center">
          <User className="h-6 w-6 text-stellar-purple" />
        </div>
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Profile</h1>
          <p className="text-muted-foreground">Manage your account and preferences</p>
        </div>
      </div>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList className="bg-white/[0.03] border border-white/[0.06] p-1 rounded-xl">
          <TabsTrigger value="profile" className="data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan rounded-lg">Profile</TabsTrigger>
          <TabsTrigger value="api" className="data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan rounded-lg">API Keys</TabsTrigger>
          <TabsTrigger value="notifications" className="data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan rounded-lg">Notifications</TabsTrigger>
          <TabsTrigger value="security" className="data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan rounded-lg">Security</TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardHeader>
              <CardTitle className="font-display">Profile Information</CardTitle>
              <CardDescription>
                Update your personal information and organization details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar */}
              <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-br from-cosmic-cyan/5 via-transparent to-stellar-purple/5">
                <div className="h-20 w-20 rounded-full bg-stellar-purple/10 border border-stellar-purple/20 flex items-center justify-center">
                  <User className="h-10 w-10 text-stellar-purple" />
                </div>
                <div>
                  <Button variant="outline" size="sm">Change Avatar</Button>
                  <p className="text-xs text-muted-foreground mt-1">JPG, PNG or GIF. 1MB max.</p>
                </div>
              </div>

              <Separator />

              {/* Form Fields */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="username">Display Name</Label>
                  <Input
                    id="username"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={user?.email ?? ''}
                    disabled
                    className="opacity-60"
                  />
                  <p className="text-xs text-muted-foreground">
                    Email is managed by your authentication provider.
                  </p>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="organization">Organization</Label>
                  <div className="flex gap-2">
                    <Building2 className="h-10 w-10 text-cosmic-cyan p-2 border border-white/[0.06] bg-white/[0.02] rounded-md" />
                    <Input
                      id="organization"
                      value={organization}
                      onChange={(e) => setOrganization(e.target.value)}
                      className="flex-1"
                    />
                  </div>
                </div>
              </div>

              {/* API Token Fields */}
              <Separator />
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium">Data Source API Tokens</h4>
                  <p className="text-sm text-muted-foreground">
                    Your API tokens are stored securely and used for dataset generation.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="udl-token">UDL API Token</Label>
                  <div className="flex gap-2">
                    <Key className="h-10 w-10 text-cosmic-cyan p-2 border border-white/[0.06] bg-white/[0.02] rounded-md" />
                    <div className="relative flex-1">
                      <Input
                        id="udl-token"
                        type={showUdlToken ? 'text' : 'password'}
                        placeholder={udlTokenMask || 'Enter your UDL API token'}
                        value={udlToken}
                        onChange={(e) => setUdlToken(e.target.value)}
                        className="pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowUdlToken(!showUdlToken)}
                      >
                        {showUdlToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="esa-token">ESA API Token</Label>
                  <div className="flex gap-2">
                    <Key className="h-10 w-10 text-cosmic-cyan p-2 border border-white/[0.06] bg-white/[0.02] rounded-md" />
                    <div className="relative flex-1">
                      <Input
                        id="esa-token"
                        type={showEsaToken ? 'text' : 'password'}
                        placeholder={esaTokenMask || 'Enter your ESA API token'}
                        value={esaToken}
                        onChange={(e) => setEsaToken(e.target.value)}
                        className="pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowEsaToken(!showEsaToken)}
                      >
                        {showEsaToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="grid gap-4 sm:grid-cols-3 pt-4 border-t border-white/[0.06]">
                <div>
                  <p className="text-sm text-muted-foreground">Member Since</p>
                  <p className="font-medium">{memberSince}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Submissions</p>
                  <p className="font-medium">{totalSubmissions}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Best Score</p>
                  <p className="font-medium">{stats?.bestScore ? stats.bestScore.toFixed(4) : '--'}</p>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSaveProfile} disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Changes'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardHeader>
              <CardTitle className="font-display">API Keys</CardTitle>
              <CardDescription>
                Manage API keys for programmatic access to the platform
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-cosmic-cyan" />
                    <span className="font-medium">Production API Key</span>
                    <Badge variant="success">Active</Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowApiKey(!showApiKey)}
                  >
                    {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-white/5 border border-white/[0.06] px-3 py-2 rounded font-mono text-sm">
                    {showApiKey ? placeholderApiKey : '\u2022'.repeat(40)}
                  </code>
                  <Button variant="outline" size="icon" onClick={handleCopyApiKey}>
                    {copiedKey ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Created: Jan 15, 2026 -- Last used: 2 hours ago
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Regenerate API Key</p>
                  <p className="text-sm text-muted-foreground">
                    This will invalidate your current key
                  </p>
                </div>
                <Button variant="destructive" className="gap-2" onClick={handleRegenerateKey}>
                  <RefreshCw className="h-4 w-4" />
                  Regenerate
                </Button>
              </div>

              <Separator />

              <div>
                <h4 className="font-medium mb-2">API Usage</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  API usage tracking coming soon
                </p>
                <div className="grid gap-2 sm:grid-cols-3">
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                    <p className="text-sm text-muted-foreground">Requests Today</p>
                    <p className="text-2xl font-bold text-muted-foreground">--</p>
                  </div>
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                    <p className="text-sm text-muted-foreground">This Month</p>
                    <p className="text-2xl font-bold text-muted-foreground">--</p>
                  </div>
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                    <p className="text-sm text-muted-foreground">Rate Limit</p>
                    <p className="text-2xl font-bold">Unlimited</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardHeader>
              <CardTitle className="font-display">Notification Preferences</CardTitle>
              <CardDescription>
                Choose what updates you want to receive
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Submission Complete</Label>
                    <p className="text-sm text-muted-foreground">
                      Get notified when your submission evaluation is complete
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Rank Changes</Label>
                    <p className="text-sm text-muted-foreground">
                      Get notified when your leaderboard position changes
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>New Datasets</Label>
                    <p className="text-sm text-muted-foreground">
                      Get notified when new benchmark datasets are available
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Platform Updates</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive announcements about new features and changes
                    </p>
                  </div>
                  <Switch />
                </div>
              </div>

              <div className="flex justify-end">
                <Button>Save Preferences</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardHeader>
              <CardTitle className="font-display">Security Settings</CardTitle>
              <CardDescription>
                Manage your account security and authentication
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Change Password */}
              <div className="space-y-4">
                <h4 className="font-medium">Change Password</h4>
                <div className="space-y-4 max-w-md">
                  <div className="space-y-2">
                    <Label htmlFor="current-password">Current Password</Label>
                    <Input id="current-password" type="password" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new-password">New Password</Label>
                    <Input id="new-password" type="password" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm New Password</Label>
                    <Input id="confirm-password" type="password" />
                  </div>
                  <Button>Update Password</Button>
                </div>
              </div>

              <Separator />

              {/* Two-Factor Authentication */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <Label>Two-Factor Authentication</Label>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Add an extra layer of security to your account
                  </p>
                </div>
                <Button variant="outline">Enable 2FA</Button>
              </div>

              <Separator />

              {/* Active Sessions */}
              <div>
                <h4 className="font-medium mb-4">Active Sessions</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                    <div>
                      <p className="font-medium">Current Session</p>
                      <p className="text-sm text-muted-foreground">
                        {user?.email ?? 'Unknown'} -- This device
                      </p>
                    </div>
                    <Badge variant="success">Active</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
