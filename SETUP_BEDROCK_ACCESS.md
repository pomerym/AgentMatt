# AWS Bedrock Claude Model Setup Required

## Status
✅ API Format Fixed - AWS Bedrock is now reachable
⚠️ Account Setup Needed - Anthropic Use Case Form Required

## What's The Error?

When you try to send a message, you get:
```
Model use case details have not been submitted for this account. 
Fill out the Anthropic use case details form before using the model.
```

## Why This Happens

AWS Bedrock requires all users to declare their intended use case for Claude models before accessing them. This is a security and compliance measure by Anthropic.

## How to Fix It

### Step 1: Open AWS Console
Go to AWS Bedrock in your AWS Console:
https://console.aws.amazon.com/bedrock/

### Step 2: Request Model Access
1. Click on "Model access" in the left sidebar
2. Look for "Anthropic" models (Claude 3, etc.)
3. Click the model name or "Edit access"
4. You'll see a notice to request access

### Step 3: Fill Out Use Case Form
1. Click "Request access" or similar button
2. Fill out the Anthropic Use Case form with:
   - **Use Case**: Describe what you're building (e.g., "AI-powered chat agent for internal tools")
   - **Intended Use**: Explain how you'll use the model
   - **Expected Volume**: Estimate your API call volume
   - **Compliance Info**: As needed

### Step 4: Wait for Approval
- Usually takes **2-15 minutes** for approval
- Check the model status in "Model access"
- Status will change from "Request submitted" to "Access granted"

### Step 5: Test Again
Once approved:
1. Restart the servers: `./restart-servers.sh`
2. Send a test message in the chat
3. You should now get real Claude responses

## Verification

After setup, logs should show:
```
[BEDROCK MESSAGE] Calling AWS Bedrock API with model: anthropic.claude-3-sonnet-20240229-v1:0
[BEDROCK MESSAGE] Successfully received response from Bedrock
```

Instead of:
```
[BEDROCK MESSAGE] Error calling AWS Bedrock: ... Model use case details ...
```

## Alternative: Use Mock Responses

If you want to test without AWS access, the code falls back to mock responses if the API call fails. You'll see messages like:
```
Mock Bedrock (anthropic.claude-3-sonnet-20240229-v1:0) response to: What is 2+2?
```

## Common Issues

### Issue: "Still seeing the error after 15 minutes"
- **Solution**: Refresh AWS Console, log out and log back in
- Sometimes the cache needs to clear

### Issue: "Request access button not showing"
- **Solution**: Ensure you're in a region that supports Claude models (us-east-1, us-west-2, etc.)
- Check your Bedrock region setting

### Issue: "Different credentials issue"
- **Solution**: Verify credentials in `backend/config/providers.json` match your AWS IAM user
- Ensure the IAM user has `bedrock:InvokeModel` permission

### Avoid Committing Secrets
Use env var placeholders in `backend/config/providers.json` and export the values
in your shell or a local `.env` file that is not committed.

## What We Fixed

The previous error was "Invalid API version: bedrock-2023-06-01". This was a formatting issue in the request sent to AWS.

**Fixed by:**
- Removing the problematic `anthropic_version` field
- Adding proper `contentType` and `accept` headers
- Using the correct Bedrock Claude API format

The code now correctly communicates with AWS Bedrock!

## Next Steps

1. **Complete the Use Case Form** in AWS Console
2. **Wait for approval** (usually 2-15 minutes)
3. **Restart servers**: `./restart-servers.sh`
4. **Test the chat** with a real message
5. **Monitor costs** in AWS Billing Dashboard

## Reference

- [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
- [Claude Model Access](https://docs.anthropic.com/en/docs/about-claude/models/model-list)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
