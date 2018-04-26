p# APB Tool V2

### Introduction
The community has been discussing apb tool V2 for some time now.  Besides the
code restructuring and refactoring, one of the reasons for a v2 is
writing the tool in GO.

The advantage of writing the apb tool in GO is that we can reuse the
ansible-service-broker and newly created [bundle-lib](https://github.com/automationbroker/bundle-lib)
libraries to build a more powerful client for APBs and possibly merge the client
into origin.

### Origin Client
Writing the apb tool in GO gives the community the opportunity to have it merged
into the origin client.  To make it easy for that to occur, we'll use the same
structure outlined in [origin cli hacking guidelines](https://github.com/openshift/origin/blob/master/docs/cli_hacking_guide.adoc#cli-code-organization).

### New Command Structure
Each command will have:
  - NewCmd<CommandName>: function that creates the command and returns a pointer to a cobra.Command.
  - <CommandName>Options: struct to hold cmd options.
  - Complete: function to complete the struct variables with values that may not be directly provided.
  - Validate: function that performs validation and returns errors.
  - Run<CommandName>: function that runs the command

```go
const APBPushCommandName = "push"

type APBPushOptions struct {
     broker string
}

// Create APBPush cmd
func NewCmdAPBPush(...) *cobra.Command {
  options := &APBPushOptions{}
  cmd := &cobra.Command{
    Use:     fmt.Sprintf("%s [--latest]", name),
    Short:   "APB push",
    Long:    APBPushLong,
    Example: fmt.Sprintf(APBPushExample),
    Run: func(cmd *cobra.Command, args []string) {
      if err := options.Complete(f, cmd, args, out); err != nil {
        cmdutil.CheckErr(err)
      }
      if err := options.Validate(args); err != nil {
        cmdutil.CheckErr(cmdutil.UsageErrorf(cmd, err.Error()))
      }
      if err := options.RunDeploy(); err != nil {
        cmdutil.CheckErr(err)
      }
    },
  }
  cmd.Flags().BoolVar(&options.broker, "", false, "Broker route")
  return cmd
}

// 'Complete' completes all the required options
func (o *APBPushOptions) Complete(f *clientcmd.Factory, cmd *cobra.Command, args []string, out io.Writer) error {
  return nil
}

// 'Validate' validates all the required options
func (o APBPushOptions) Validate() error {
  return nil
}

// RunAPBPush implements all the necessary functionality
func (o APBPushOptions) RunAPBPush() error {
  return nil
}
```

### main.go
The main.go function will keep a list of commands

```go
func NewCLI(...) *cobra.Command {
     cmd.NewCmd<CommandName>(...)
}
```

### Release Target
3.11 is a good preliminary target.
