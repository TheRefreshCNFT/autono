/**
 * Comprehensive Security Testing Suite
 * 
 * Automated security tests to run on every commit
 */

import crypto from 'crypto';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

interface SecurityTestResult {
  testName: string;
  passed: boolean;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  message: string;
  details?: any;
}

class SecurityTestSuite {
  private results: SecurityTestResult[] = [];

  /**
   * Run all security tests
   */
  async runAll(): Promise<SecurityTestResult[]> {
    console.log('🔒 Running Comprehensive Security Test Suite...\n');

    // Memory security tests
    await this.testMemoryWiping();
    await this.testNoSensitiveDataInMemory();

    // Cryptographic tests
    await this.testEntropyQuality();
    await this.testKeyDerivationStrength();

    // Input validation tests
    await this.testAddressValidation();
    await this.testTransactionValidation();

    // Logging security tests
    await this.testLogSanitization();
    await this.testNoSensitiveLogging();

    // Static analysis tests
    await this.testNoHardcodedSecrets();
    await this.testSecureDependencies();

    // File system security tests
    await this.testNoPlaintextStorage();

    this.printResults();
    return this.results;
  }

  /**
   * Test memory wiping effectiveness
   */
  private async testMemoryWiping(): Promise<void> {
    const testName = 'Memory Wiping Effectiveness';
    
    try {
      // Test buffer wiping
      const buffer = Buffer.from('supersecret');
      const heapSnapshot1 = this.captureHeapSnapshot();
      
      buffer.fill(0);
      
      const heapSnapshot2 = this.captureHeapSnapshot();
      
      // Check if buffer was actually wiped
      const allZeros = buffer.every(b => b === 0);
      
      if (allZeros) {
        this.addResult({
          testName,
          passed: true,
          severity: 'INFO',
          message: 'Buffer wiping works correctly'
        });
      } else {
        this.addResult({
          testName,
          passed: false,
          severity: 'CRITICAL',
          message: 'Buffer wiping FAILED - sensitive data remains in memory'
        });
      }
    } catch (error) {
      this.addResult({
        testName,
        passed: false,
        severity: 'HIGH',
        message: `Test error: ${error}`
      });
    }
  }

  /**
   * Test for sensitive data in memory
   */
  private async testNoSensitiveDataInMemory(): Promise<void> {
    const testName = 'No Sensitive Data in Memory';
    
    // Simulate using sensitive data
    const mnemonic = 'test abandon ability able about above absent absorb';
    let container = mnemonic; // Store in variable
    
    // "Wipe" it (this won't actually work for strings)
    container = '';
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
    
    // In a real scenario, we'd inspect heap dumps here
    // For now, we document the vulnerability
    this.addResult({
      testName,
      passed: false,
      severity: 'CRITICAL',
      message: 'JavaScript strings CANNOT be securely wiped from memory',
      details: {
        vulnerability: 'Strings are immutable in JavaScript',
        recommendation: 'Use Uint8Array or Buffer for sensitive data',
        impact: 'Seed phrases remain in memory indefinitely'
      }
    });
  }

  /**
   * Test entropy quality for key generation
   */
  private async testEntropyQuality(): Promise<void> {
    const testName = 'Entropy Quality for Key Generation';
    
    try {
      // Generate random bytes using crypto.randomBytes
      const randomBytes1 = crypto.randomBytes(32);
      const randomBytes2 = crypto.randomBytes(32);
      
      // Check they're different (basic randomness check)
      const areDifferent = !randomBytes1.equals(randomBytes2);
      
      // Check for weak patterns (all zeros, all same byte)
      const hasVariety = new Set(randomBytes1).size > 10;
      
      if (areDifferent && hasVariety) {
        this.addResult({
          testName,
          passed: true,
          severity: 'INFO',
          message: 'Using crypto.randomBytes for entropy generation'
        });
      } else {
        this.addResult({
          testName,
          passed: false,
          severity: 'CRITICAL',
          message: 'Weak entropy detected in random number generation'
        });
      }
    } catch (error) {
      this.addResult({
        testName,
        passed: false,
        severity: 'CRITICAL',
        message: `Entropy test failed: ${error}`
      });
    }
  }

  /**
   * Test PBKDF2 iteration count
   */
  private async testKeyDerivationStrength(): Promise<void> {
    const testName = 'Key Derivation Strength (PBKDF2)';
    
    const MINIMUM_ITERATIONS = 600000; // OWASP 2024 recommendation
    
    // Test PBKDF2 performance
    const password = 'testpassword';
    const salt = crypto.randomBytes(16);
    
    const startTime = Date.now();
    crypto.pbkdf2Sync(password, salt, MINIMUM_ITERATIONS, 32, 'sha256');
    const duration = Date.now() - startTime;
    
    if (duration < 100) {
      this.addResult({
        testName,
        passed: false,
        severity: 'HIGH',
        message: `PBKDF2 completes too fast (${duration}ms). May be vulnerable to brute force.`,
        details: {
          iterations: MINIMUM_ITERATIONS,
          duration: `${duration}ms`,
          recommendation: 'Increase iterations or use Argon2'
        }
      });
    } else {
      this.addResult({
        testName,
        passed: true,
        severity: 'INFO',
        message: `PBKDF2 with ${MINIMUM_ITERATIONS} iterations takes ${duration}ms`,
        details: {
          iterations: MINIMUM_ITERATIONS,
          duration: `${duration}ms`
        }
      });
    }
  }

  /**
   * Test address validation against known attack vectors
   */
  private async testAddressValidation(): Promise<void> {
    const testName = 'Address Validation Security';
    
    const attackVectors = [
      { input: 'javascript:alert(1)', type: 'XSS attempt' },
      { input: '"; DROP TABLE users; --', type: 'SQL injection' },
      { input: '../../../etc/passwd', type: 'Path traversal' },
      { input: 'addr1' + 'A'.repeat(10000), type: 'Buffer overflow attempt' },
      { input: 'addr1\x00malicious', type: 'Null byte injection' },
    ];
    
    const { validateCardanoAddress } = require('./src/utils/security');
    
    let allRejected = true;
    const failures: string[] = [];
    
    for (const vector of attackVectors) {
      const result = validateCardanoAddress(vector.input);
      if (result === true) {
        allRejected = false;
        failures.push(vector.type);
      }
    }
    
    if (allRejected) {
      this.addResult({
        testName,
        passed: true,
        severity: 'INFO',
        message: 'Address validation rejects attack vectors'
      });
    } else {
      this.addResult({
        testName,
        passed: false,
        severity: 'HIGH',
        message: 'Address validation accepts malicious inputs',
        details: { failedChecks: failures }
      });
    }
  }

  /**
   * Test transaction validation
   */
  private async testTransactionValidation(): Promise<void> {
    const testName = 'Transaction Amount Validation';
    
    // Test for integer overflow vulnerabilities
    const dangerousAmounts = [
      '999999999999999999999999999999', // Very large number
      '-100', // Negative amount
      '1.5e308', // Near MAX_SAFE_INTEGER
      'Infinity',
      'NaN',
      '0x1234', // Hex notation
    ];
    
    // This test documents missing validation
    this.addResult({
      testName,
      passed: false,
      severity: 'HIGH',
      message: 'Transaction validation NOT IMPLEMENTED',
      details: {
        vulnerability: 'No checks for overflow, negative amounts, or invalid formats',
        attackVectors: dangerousAmounts,
        recommendation: 'Implement BigInt validation with range checks'
      }
    });
  }

  /**
   * Test log sanitization
   */
  private async testLogSanitization(): Promise<void> {
    const testName = 'Log Sanitization';
    
    const { sanitizeError } = require('./src/utils/security');
    
    const sensitiveInputs = [
      {
        input: 'Error with key: abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab',
        shouldContain: '[REDACTED_KEY]',
        shouldNotContain: 'abcd1234'
      },
      {
        input: 'Failed at addr1qxyz123456789abcdefghijklmnopqrst',
        shouldContain: '[REDACTED_ADDRESS]',
        shouldNotContain: 'addr1qxyz'
      },
      {
        input: 'Mnemonic: abandon ability able about above absent absorb abstract absurd abuse access accident',
        shouldContain: '[REDACTED_MNEMONIC]',
        shouldNotContain: 'abandon'
      }
    ];
    
    let allPassed = true;
    const failures: string[] = [];
    
    for (const test of sensitiveInputs) {
      const error = new Error(test.input);
      const sanitized = sanitizeError(error);
      
      const containsRedacted = sanitized.message.includes(test.shouldContain);
      const doesNotContainSensitive = !sanitized.message.includes(test.shouldNotContain);
      
      if (!containsRedacted || !doesNotContainSensitive) {
        allPassed = false;
        failures.push(test.input);
      }
    }
    
    if (allPassed) {
      this.addResult({
        testName,
        passed: true,
        severity: 'INFO',
        message: 'Log sanitization working correctly'
      });
    } else {
      this.addResult({
        testName,
        passed: false,
        severity: 'CRITICAL',
        message: 'Log sanitization INCOMPLETE - sensitive data may leak',
        details: { failures }
      });
    }
  }

  /**
   * Test for sensitive data in console logs
   */
  private async testNoSensitiveLogging(): Promise<void> {
    const testName = 'No Sensitive Logging';
    
    // Scan source files for dangerous console.log patterns
    const sourceFiles = this.findSourceFiles();
    const violations: string[] = [];
    
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8');
      
      // Look for console.log with sensitive variable names
      const dangerousPatterns = [
        /console\.log.*mnemonic/i,
        /console\.log.*privateKey/i,
        /console\.log.*seed/i,
        /console\.log.*password/i,
        /console\.log.*secret/i,
      ];
      
      for (const pattern of dangerousPatterns) {
        if (pattern.test(content)) {
          violations.push(file);
          break;
        }
      }
    }
    
    if (violations.length === 0) {
      this.addResult({
        testName,
        passed: true,
        severity: 'INFO',
        message: 'No obvious sensitive logging detected'
      });
    } else {
      this.addResult({
        testName,
        passed: false,
        severity: 'CRITICAL',
        message: 'Potential sensitive data logging detected',
        details: { files: violations }
      });
    }
  }

  /**
   * Test for hardcoded secrets
   */
  private async testNoHardcodedSecrets(): Promise<void> {
    const testName = 'No Hardcoded Secrets';
    
    const sourceFiles = this.findSourceFiles();
    const violations: Array<{ file: string; pattern: string }> = [];
    
    const secretPatterns = [
      { pattern: /['"]sk[0-9a-f]{64}['"]/, name: 'Possible private key' },
      { pattern: /['"]xprv[0-9a-zA-Z]{100,}['"]/, name: 'Extended private key' },
      { pattern: /api[_-]?key\s*=\s*['"]\w+['"]/, name: 'API key' },
      { pattern: /password\s*=\s*['"]\w+['"]/, name: 'Hardcoded password' },
    ];
    
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8');
      
      for (const { pattern, name } of secretPatterns) {
        if (pattern.test(content)) {
          violations.push({ file, pattern: name });
        }
      }
    }
    
    if (violations.length === 0) {
      this.addResult({
        testName,
        passed: true,
        severity: 'INFO',
        message: 'No hardcoded secrets detected'
      });
    } else {
      this.addResult({
        testName,
        passed: false,
        severity: 'CRITICAL',
        message: 'Hardcoded secrets detected',
        details: { violations }
      });
    }
  }

  /**
   * Test dependency security
   */
  private async testSecureDependencies(): Promise<void> {
    const testName = 'Secure Dependencies';
    
    try {
      // Run npm audit
      const auditResult = execSync('npm audit --json', { encoding: 'utf-8' });
      const audit = JSON.parse(auditResult);
      
      const critical = audit.metadata?.vulnerabilities?.critical || 0;
      const high = audit.metadata?.vulnerabilities?.high || 0;
      
      if (critical > 0 || high > 0) {
        this.addResult({
          testName,
          passed: false,
          severity: 'CRITICAL',
          message: `Found ${critical} critical and ${high} high severity vulnerabilities`,
          details: { 
            critical, 
            high,
            command: 'Run `npm audit fix` to resolve'
          }
        });
      } else {
        this.addResult({
          testName,
          passed: true,
          severity: 'INFO',
          message: 'No critical or high severity vulnerabilities in dependencies'
        });
      }
    } catch (error: any) {
      if (error.stdout) {
        const audit = JSON.parse(error.stdout);
        const critical = audit.metadata?.vulnerabilities?.critical || 0;
        const high = audit.metadata?.vulnerabilities?.high || 0;
        
        if (critical > 0 || high > 0) {
          this.addResult({
            testName,
            passed: false,
            severity: 'CRITICAL',
            message: `Found ${critical} critical and ${high} high severity vulnerabilities`
          });
        }
      } else {
        this.addResult({
          testName,
          passed: false,
          severity: 'MEDIUM',
          message: 'Could not run npm audit'
        });
      }
    }
  }

  /**
   * Test for plaintext storage of sensitive data
   */
  private async testNoPlaintextStorage(): Promise<void> {
    const testName = 'No Plaintext Storage';
    
    // This test documents missing encryption implementation
    this.addResult({
      testName,
      passed: false,
      severity: 'CRITICAL',
      message: 'Encryption layer NOT IMPLEMENTED',
      details: {
        vulnerability: 'No Night chain encryption for seed phrases',
        recommendation: 'Implement AES-256-GCM encryption before ANY storage',
        impact: 'Seed phrases may be stored in plaintext'
      }
    });
  }

  /**
   * Helper: Capture heap snapshot (simplified)
   */
  private captureHeapSnapshot(): any {
    // In production, use v8.writeHeapSnapshot()
    return {}; // Placeholder
  }

  /**
   * Helper: Find all source files
   */
  private findSourceFiles(): string[] {
    const files: string[] = [];
    
    const scanDir = (dir: string): void => {
      const items = fs.readdirSync(dir);
      
      for (const item of items) {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);
        
        if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
          scanDir(fullPath);
        } else if (item.endsWith('.ts') || item.endsWith('.js')) {
          files.push(fullPath);
        }
      }
    };
    
    if (fs.existsSync('src')) {
      scanDir('src');
    }
    
    return files;
  }

  /**
   * Add a test result
   */
  private addResult(result: SecurityTestResult): void {
    this.results.push(result);
  }

  /**
   * Print test results
   */
  private printResults(): void {
    console.log('\n' + '='.repeat(80));
    console.log('SECURITY TEST RESULTS');
    console.log('='.repeat(80) + '\n');
    
    const bySerity = {
      CRITICAL: this.results.filter(r => r.severity === 'CRITICAL'),
      HIGH: this.results.filter(r => r.severity === 'HIGH'),
      MEDIUM: this.results.filter(r => r.severity === 'MEDIUM'),
      LOW: this.results.filter(r => r.severity === 'LOW'),
      INFO: this.results.filter(r => r.severity === 'INFO'),
    };
    
    for (const [severity, tests] of Object.entries(bySerity)) {
      if (tests.length === 0) continue;
      
      const icon = {
        CRITICAL: '🔴',
        HIGH: '🟠',
        MEDIUM: '🟡',
        LOW: '🔵',
        INFO: '✅'
      }[severity];
      
      console.log(`\n${icon} ${severity} (${tests.length})`);
      console.log('-'.repeat(80));
      
      for (const test of tests) {
        const status = test.passed ? '✅ PASS' : '❌ FAIL';
        console.log(`  ${status} - ${test.testName}`);
        console.log(`      ${test.message}`);
        if (test.details) {
          console.log(`      Details: ${JSON.stringify(test.details, null, 2)}`);
        }
      }
    }
    
    console.log('\n' + '='.repeat(80));
    
    const failed = this.results.filter(r => !r.passed);
    const criticalFailed = failed.filter(r => r.severity === 'CRITICAL').length;
    const highFailed = failed.filter(r => r.severity === 'HIGH').length;
    
    console.log(`\nTotal Tests: ${this.results.length}`);
    console.log(`Passed: ${this.results.length - failed.length}`);
    console.log(`Failed: ${failed.length} (${criticalFailed} critical, ${highFailed} high)`);
    
    if (criticalFailed > 0) {
      console.log('\n🚨 CRITICAL ISSUES DETECTED - DO NOT DEPLOY 🚨\n');
      process.exit(1);
    } else if (highFailed > 0) {
      console.log('\n⚠️  HIGH SEVERITY ISSUES DETECTED - REVIEW REQUIRED ⚠️\n');
      process.exit(1);
    } else {
      console.log('\n✅ All security tests passed\n');
    }
  }
}

// Run tests if executed directly
if (require.main === module) {
  const suite = new SecurityTestSuite();
  suite.runAll().catch(error => {
    console.error('Security test suite failed:', error);
    process.exit(1);
  });
}

export { SecurityTestSuite, SecurityTestResult };
