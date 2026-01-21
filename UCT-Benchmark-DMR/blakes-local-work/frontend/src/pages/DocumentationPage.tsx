import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Code, FileJson, BarChart3, Rocket } from 'lucide-react';

export function DocumentationPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Documentation</h1>
        <p className="text-muted-foreground mt-1">
          Learn how to use the SpOC UCT Benchmark Platform
        </p>
      </div>

      <Tabs defaultValue="getting-started" className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-2">
          <TabsTrigger value="getting-started" className="gap-2">
            <Rocket className="h-4 w-4" />
            Getting Started
          </TabsTrigger>
          <TabsTrigger value="dataset-format" className="gap-2">
            <FileJson className="h-4 w-4" />
            Dataset Format
          </TabsTrigger>
          <TabsTrigger value="submission-format" className="gap-2">
            <Code className="h-4 w-4" />
            Submission Format
          </TabsTrigger>
          <TabsTrigger value="metrics" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Evaluation Metrics
          </TabsTrigger>
        </TabsList>

        {/* Getting Started */}
        <TabsContent value="getting-started">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Rocket className="h-5 w-5" />
                Getting Started
              </CardTitle>
              <CardDescription>
                Quick start guide for the SpOC UCT Benchmark Platform
              </CardDescription>
            </CardHeader>
            <CardContent className="prose dark:prose-invert max-w-none">
              <h3>Welcome to SpOC</h3>
              <p>
                The SpOC (Space Operations Center) UCT Benchmark Platform is a standardized framework
                for evaluating Uncorrelated Track (UCT) processing algorithms. This guide will help
                you get started with generating datasets, submitting your algorithm results, and
                understanding your performance metrics.
              </p>

              <h3>Quick Start Steps</h3>
              <ol>
                <li>
                  <strong>Generate a Dataset</strong> - Navigate to Datasets &gt; Generate and configure
                  your benchmark dataset parameters. Start with the "Easy" preset for your first run.
                </li>
                <li>
                  <strong>Download the Dataset</strong> - Once generated, download the dataset JSON file
                  containing observations and the truth catalog.
                </li>
                <li>
                  <strong>Run Your Algorithm</strong> - Process the observations with your UCT algorithm
                  to produce track associations and state estimates.
                </li>
                <li>
                  <strong>Submit Results</strong> - Upload your algorithm output through the Submit page.
                  The system will validate your submission and run the evaluation pipeline.
                </li>
                <li>
                  <strong>View Results</strong> - Once evaluation is complete, view your detailed results
                  and compare against the leaderboard.
                </li>
              </ol>

              <h3>Key Concepts</h3>
              <h4>Orbital Regimes</h4>
              <ul>
                <li><Badge variant="leo">LEO</Badge> - Low Earth Orbit (200-2000 km altitude)</li>
                <li><Badge variant="meo">MEO</Badge> - Medium Earth Orbit (2000-35,786 km altitude)</li>
                <li><Badge variant="geo">GEO</Badge> - Geostationary Orbit (35,786 km altitude)</li>
                <li><Badge variant="heo">HEO</Badge> - Highly Elliptical Orbit (variable altitude)</li>
              </ul>

              <h4>Data Tiers</h4>
              <ul>
                <li><Badge variant="tier1">T1</Badge> - Pristine: High-quality, complete observations</li>
                <li><Badge variant="tier2">T2</Badge> - Downsampled: Realistic sparse coverage</li>
                <li><Badge variant="tier3">T3</Badge> - Simulated Obs: Synthetic observations from real orbits</li>
                <li><Badge variant="tier4">T4</Badge> - Synthetic: Fully simulated objects and observations</li>
              </ul>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dataset Format */}
        <TabsContent value="dataset-format">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileJson className="h-5 w-5" />
                Dataset Format Specification
              </CardTitle>
              <CardDescription>
                Understand the structure of benchmark datasets
              </CardDescription>
            </CardHeader>
            <CardContent className="prose dark:prose-invert max-w-none">
              <h3>Dataset Structure</h3>
              <p>
                Each benchmark dataset is provided as a JSON file containing two main sections:
                observations and the truth catalog.
              </p>

              <h4>Observations Schema</h4>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`{
  "observations": [
    {
      "obsId": "string",           // Unique observation identifier
      "time": "ISO8601 datetime",  // Observation epoch
      "ra": number,                // Right Ascension (degrees)
      "dec": number,               // Declination (degrees)
      "raRate": number,            // RA rate (deg/sec) - optional
      "decRate": number,           // Dec rate (deg/sec) - optional
      "raSigma": number,           // RA uncertainty (arcsec)
      "decSigma": number,          // Dec uncertainty (arcsec)
      "sensorId": "string",        // Sensor identifier
      "trackId": "string"          // Track grouping identifier
    }
  ]
}`}
              </pre>

              <h4>Truth Catalog Schema</h4>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`{
  "truthCatalog": [
    {
      "satId": "string",           // NORAD catalog ID or synthetic ID
      "epoch": "ISO8601 datetime", // State epoch
      "state": [x, y, z, vx, vy, vz], // ECI state vector (km, km/s)
      "covariance": [...]          // 6x6 covariance matrix (optional)
    }
  ]
}`}
              </pre>

              <h4>Association Ground Truth</h4>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`{
  "associations": {
    "trackId_001": "satId_25544",
    "trackId_002": "satId_25545",
    ...
  }
}`}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Submission Format */}
        <TabsContent value="submission-format">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Submission Format Specification
              </CardTitle>
              <CardDescription>
                Format your algorithm output for evaluation
              </CardDescription>
            </CardHeader>
            <CardContent className="prose dark:prose-invert max-w-none">
              <h3>Submission Structure</h3>
              <p>
                Your submission should be a JSON file containing your algorithm's track associations
                and state estimates for each identified object.
              </p>

              <h4>Required Schema</h4>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`{
  "metadata": {
    "algorithmName": "string",
    "version": "string",
    "datasetId": "string",
    "timestamp": "ISO8601 datetime"
  },
  "results": [
    {
      "objectId": "string",        // Your algorithm's object ID
      "trackIds": ["string"],      // Associated track IDs
      "state": {
        "epoch": "ISO8601 datetime",
        "position": [x, y, z],     // km in ECI
        "velocity": [vx, vy, vz],  // km/s in ECI
        "covariance": [...]        // 6x6 matrix (km^2, km^2/s, km^2/s^2)
      },
      "confidence": number         // 0.0 to 1.0
    }
  ]
}`}
              </pre>

              <h4>Validation Rules</h4>
              <ul>
                <li>All referenced track IDs must exist in the dataset</li>
                <li>State vectors must be in Earth-Centered Inertial (ECI) frame</li>
                <li>Covariance matrices must be positive semi-definite</li>
                <li>Position magnitudes must be physically reasonable (above Earth surface)</li>
                <li>Velocity magnitudes must be consistent with orbital mechanics</li>
              </ul>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Metrics */}
        <TabsContent value="metrics">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Evaluation Metrics
              </CardTitle>
              <CardDescription>
                Understanding how your algorithm is scored
              </CardDescription>
            </CardHeader>
            <CardContent className="prose dark:prose-invert max-w-none">
              <h3>Binary Classification Metrics</h3>
              <p>
                Track associations are evaluated as a binary classification problem:
              </p>
              <ul>
                <li><strong>True Positive (TP)</strong>: Correctly associated track to catalog object</li>
                <li><strong>False Positive (FP)</strong>: Incorrectly associated track (wrong object or non-existent)</li>
                <li><strong>False Negative (FN)</strong>: Missed association (catalog object not tracked)</li>
              </ul>

              <h4>Primary Metrics</h4>
              <ul>
                <li><strong>Precision</strong> = TP / (TP + FP) - How many of your associations are correct?</li>
                <li><strong>Recall</strong> = TP / (TP + FN) - How many catalog objects did you find?</li>
                <li><strong>F1-Score</strong> = 2 × (Precision × Recall) / (Precision + Recall) - Harmonic mean</li>
              </ul>

              <h3>State Estimation Metrics</h3>
              <p>
                For correctly associated objects, we evaluate state estimation accuracy:
              </p>
              <ul>
                <li><strong>Position RMS</strong> - Root mean square error in position (km)</li>
                <li><strong>Velocity RMS</strong> - Root mean square error in velocity (km/s)</li>
                <li><strong>Mahalanobis Distance</strong> - Normalized error accounting for covariance</li>
              </ul>

              <h3>Residual Analysis</h3>
              <p>
                Observation residuals indicate orbit determination quality:
              </p>
              <ul>
                <li><strong>RA Residual RMS</strong> - Right ascension fit quality (arcsec)</li>
                <li><strong>Dec Residual RMS</strong> - Declination fit quality (arcsec)</li>
              </ul>

              <h3>Leaderboard Ranking</h3>
              <p>
                Algorithms are ranked primarily by F1-Score. In case of ties, position RMS is used
                as a secondary criterion (lower is better).
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
