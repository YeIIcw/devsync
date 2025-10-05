"""GitHub integration tool for creating branches, commits, and PRs."""

from github import Github, GithubException
from typing import Dict, Any, List, Optional
from config import Config
import base64
import re

class GitHubTool:
    """Tool for interacting with GitHub."""
    
    def __init__(self):
        """Initialize GitHub client."""
        self.github = Github(Config.GITHUB_TOKEN)
        owner, repo_name = Config.get_github_owner_repo()
        self.repo = self.github.get_repo(f"{owner}/{repo_name}")
        self.default_branch = Config.GITHUB_DEFAULT_BRANCH
    
    def create_fix_branch(self, issue_key: str, bug_title: str) -> str:
        """Create a new branch for the fix.
        
        Args:
            issue_key: Jira issue key (e.g., CCS-123)
            bug_title: Bug title for branch name
            
        Returns:
            Created branch name
        """
        # Clean title for branch name
        clean_title = re.sub(r'[^a-zA-Z0-9-]', '-', bug_title.lower())
        clean_title = re.sub(r'-+', '-', clean_title)[:30]
        
        branch_name = f"fix/{issue_key.lower()}-{clean_title}"
        
        try:
            # Get base branch ref
            base_branch = self.repo.get_branch(self.default_branch)
            
            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_branch.commit.sha
            )
            
            return branch_name
            
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                # Add timestamp or counter
                import time
                branch_name = f"{branch_name}-{int(time.time())}"
                self.repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=base_branch.commit.sha
                )
                return branch_name
            raise
    
    def apply_unified_diff(self, branch_name: str, patches: List[Dict[str, Any]], 
                          commit_message: str) -> bool:
        """Apply unified diffs to the branch.
        
        Args:
            branch_name: Target branch name
            patches: List of patches [{path, unified_diff}]
            commit_message: Commit message
            
        Returns:
            Success status
        """
        if not patches:
            print("No patches to apply")
            return False
        
        print(f"Applying {len(patches)} patches to branch {branch_name}")
        
        try:
            for idx, patch in enumerate(patches):
                file_path = patch.get('path', '')
                diff = patch.get('unified_diff', '')
                
                if not file_path or not diff:
                    print(f"  Skipping patch {idx+1}: missing path or diff")
                    continue
                
                print(f"  Applying patch to {file_path}")
                
                # Get current file content
                try:
                    file_obj = self.repo.get_contents(file_path, ref=branch_name)
                    current_content = base64.b64decode(file_obj.content).decode('utf-8')
                    
                    # Apply the diff manually (simple approach for now)
                    new_content = self._apply_diff_to_content(current_content, diff)
                    
                    if new_content:
                        self.repo.update_file(
                            path=file_path,
                            message=commit_message or f"fix: Apply patch to {file_path}",
                            content=new_content,
                            sha=file_obj.sha,
                            branch=branch_name
                        )
                        print(f"    ✓ Applied patch to {file_path}")
                    else:
                        print(f"    ✗ Failed to apply diff to {file_path}")
                        return False
                        
                except Exception as e:
                    print(f"    ✗ Error applying patch: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error applying patches: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _apply_diff_to_content(self, original: str, diff: str) -> str:
        """Apply a unified diff to content (simplified implementation).
        
        For production, use a proper patch library.
        """
        if not diff or not original:
            return original
            
        print(f"Applying diff to content (original: {len(original)} chars, diff: {len(diff)} chars)")
        
        # Parse the unified diff
        diff_lines = diff.splitlines()
        original_lines = original.splitlines()
        
        # Find the hunk headers (lines starting with @@)
        hunks = []
        current_hunk = None
        
        for line in diff_lines:
            if line.startswith('@@'):
                # Parse hunk header: @@ -start,count +start,count @@
                parts = line.split()
                if len(parts) >= 2:
                    old_range = parts[1]  # -start,count
                    new_range = parts[2] if len(parts) > 2 else old_range  # +start,count
                    
                    old_start = int(old_range.split(',')[0][1:])  # Remove '-' and get start
                    new_start = int(new_range.split(',')[0][1:])  # Remove '+' and get start
                    
                    current_hunk = {
                        'old_start': old_start - 1,  # Convert to 0-based
                        'new_start': new_start - 1,  # Convert to 0-based
                        'changes': []
                    }
                    hunks.append(current_hunk)
            elif current_hunk and line.startswith(('+', '-', ' ')):
                current_hunk['changes'].append(line)
        
        if not hunks:
            print("No valid hunks found in diff")
            return original
        
        # Apply hunks to original content
        result_lines = original_lines.copy()
        
        # Process hunks in reverse order to maintain line numbers
        for hunk in reversed(hunks):
            old_start = hunk['old_start']
            changes = hunk['changes']
            
            # Count lines to remove and add
            lines_to_remove = sum(1 for line in changes if line.startswith('-'))
            lines_to_add = sum(1 for line in changes if line.startswith('+'))
            
            # Remove old lines
            if lines_to_remove > 0:
                end_idx = min(old_start + lines_to_remove, len(result_lines))
                del result_lines[old_start:end_idx]
            
            # Add new lines
            new_lines = []
            for line in changes:
                if line.startswith('+'):
                    new_lines.append(line[1:])  # Remove '+' prefix
                elif line.startswith(' '):
                    new_lines.append(line[1:])  # Remove ' ' prefix
            
            # Insert new lines
            for i, new_line in enumerate(new_lines):
                result_lines.insert(old_start + i, new_line)
        
        result = '\n'.join(result_lines)
        
        # Check if changes were actually made
        if result != original:
            print(f"Successfully applied diff: {len(original)} -> {len(result)} chars")
            return result
        else:
            print("No changes detected after applying diff")
            return original
    
    def apply_code_changes(self, branch_name: str, code_changes: List[Dict[str, Any]], 
                          commit_message: str) -> bool:
        """Apply code changes to the branch.
        
        Args:
            branch_name: Target branch name
            code_changes: List of file changes [{file, changes}]
            commit_message: Commit message
            
        Returns:
            Success status
        """
        if not code_changes:
            print("No code changes to apply")
            return False
        
        print(f"Applying {len(code_changes)} code changes to branch {branch_name}")
        
        try:
            for idx, change in enumerate(code_changes):
                file_path = change.get('file', '')
                changes = change.get('changes', '')
                
                print(f"  Processing change {idx+1}: {file_path}")
                print(f"    Change type: {type(changes)}, Content length: {len(str(changes))}")
                
                if not file_path:
                    print(f"    Skipping - no file path specified")
                    continue
                    
                if not changes:
                    print(f"    Skipping - no changes specified")
                    continue
                
                # Ensure changes is a string
                if not isinstance(changes, str):
                    changes = str(changes)
                
                print(f"    Changes preview: {changes[:200]}...")
                print(f"    Changes length: {len(changes)} characters")
                
                # Try to get existing file
                try:
                    file_content = self.repo.get_contents(file_path, ref=branch_name)
                    current_content = base64.b64decode(file_content.content).decode('utf-8')
                    
                    print(f"    Updating existing file: {file_path}")
                    print(f"    Current file length: {len(current_content)} chars")
                    print(f"    New content length: {len(changes)} chars")
                    
                    # Validate that changes are reasonable
                    if len(changes) < 10:
                        print(f"    Warning: New content is very short ({len(changes)} chars)")
                    elif len(changes) > len(current_content) * 2:
                        print(f"    Warning: New content is much longer than original")
                    elif len(changes) < len(current_content) * 0.1:
                        print(f"    Warning: New content is much shorter than original")
                    
                    # Check if it's a simple text replacement
                    if len(current_content) > 100 and len(changes) > 100:
                        # Look for the actual change
                        lines_changed = 0
                        current_lines = current_content.splitlines()
                        new_lines = changes.splitlines()
                        
                        for i, (old_line, new_line) in enumerate(zip(current_lines, new_lines)):
                            if old_line != new_line:
                                lines_changed += 1
                                if lines_changed <= 3:  # Show first 3 changes
                                    print(f"      Line {i+1}: '{old_line}' → '{new_line}'")
                        
                        print(f"    Total lines changed: {lines_changed} out of {len(current_lines)}")
                    
                    # Update existing file
                    self.repo.update_file(
                        path=file_path,
                        message=f"Fix: Update {file_path}",
                        content=changes,
                        sha=file_content.sha,
                        branch=branch_name
                    )
                    print(f"    Updated {file_path}")
                except Exception as e:
                    # Create new file if doesn't exist
                    print(f"    File doesn't exist, creating new: {file_path}")
                    try:
                        self.repo.create_file(
                            path=file_path,
                            message=f"Fix: Create {file_path}",
                            content=changes,
                            branch=branch_name
                        )
                        print(f"    Created {file_path}")
                    except Exception as create_error:
                        print(f"    Failed to create {file_path}: {create_error}")
                        raise
            
            return True
            
        except Exception as e:
            print(f"Error applying code changes: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_pull_request(self, branch_name: str, issue_key: str, 
                           bug_report: Dict[str, Any], fix: Dict[str, Any]) -> str:
        """Create a pull request.
        
        Args:
            branch_name: Source branch name
            issue_key: Jira issue key
            bug_report: Original bug report
            fix: Fix details
            
        Returns:
            PR URL
        """
        title = f"[{issue_key}] Fix: {bug_report.get('title', 'Bug fix')}"
        
        # Build PR body
        body = self._format_pr_body(issue_key, bug_report, fix)
        
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=self.default_branch
            )
            
            # Add labels if available
            try:
                labels = []
                
                # Add severity label
                severity = bug_report.get('severity', 'Medium').lower()
                if severity in ['critical', 'high', 'medium', 'low']:
                    labels.append(f"severity:{severity}")
                
                # Add bug label
                labels.append('bug')
                
                # Add auto-generated label
                labels.append('auto-generated')
                
                pr.add_to_labels(*labels)
            except:
                pass  # Labels might not exist in repo
            
            return pr.html_url
            
        except Exception as e:
            print(f"Error creating PR: {e}")
            raise
    
    def _format_pr_body(self, issue_key: str, bug_report: Dict[str, Any], 
                        fix: Dict[str, Any]) -> str:
        """Format PR description.
        
        Args:
            issue_key: Jira issue key
            bug_report: Bug report data
            fix: Fix details
            
        Returns:
            Formatted PR body
        """
        sections = []
        
        # Header
        sections.append(f"## 🐛 Bug Fix for {issue_key}")
        sections.append(f"**Jira:** [{issue_key}](https://{Config.JIRA_BASE_URL}/browse/{issue_key})")
        
        # Problem
        sections.append("## Problem")
        sections.append(bug_report.get('description', 'See Jira ticket for details'))
        
        # Root Cause
        if fix.get('root_cause'):
            sections.append("## Root Cause")
            sections.append(fix['root_cause'])
        
        # Solution
        sections.append("## Solution")
        sections.append(fix.get('fix_description', 'Applied automated fix'))
        
        # Changes
        if fix.get('code_changes'):
            sections.append("## Files Modified")
            for change in fix['code_changes']:
                if change.get('file'):
                    sections.append(f"- `{change['file']}`")
        
        # Testing
        sections.append("## Testing")
        sections.append(fix.get('testing_notes', '- [ ] Manual testing required'))
        sections.append("- [ ] Code review completed")
        sections.append("- [ ] Tests pass")
        
        # Footer
        sections.append("---")
        sections.append("*This PR was automatically generated by DevSync Bot*")
        
        return "\n\n".join(sections)
    
    def get_relevant_files(self, keywords: List[str], max_files: int = 10) -> List[Dict[str, str]]:
        """Get relevant files from repository based on keywords.
        
        Args:
            keywords: Keywords to search
            max_files: Maximum files to return
            
        Returns:
            List of relevant files with COMPLETE content
        """
        relevant_files = []
        seen_paths = set()
        
        try:
            # Try multiple search strategies for better context
            # Build smarter queries based on keywords
            primary_keywords = [k for k in keywords if len(k) > 3 and k[0].isupper()]  # Component names
            
            search_queries = []
            
            # Direct file name search if it looks like a filename
            file_keywords = [k for k in keywords if '.tsx' in k or '.ts' in k or '.jsx' in k]
            if file_keywords:
                search_queries.append(f"repo:{Config.GITHUB_REPO} filename:{file_keywords[0]}")
            
            # Component search
            if primary_keywords:
                search_queries.append(f"repo:{Config.GITHUB_REPO} " + " OR ".join(primary_keywords[:2]))
            
            # Text content search
            if keywords:
                search_queries.append(f"repo:{Config.GITHUB_REPO} " + " ".join(keywords[:3]))
            
            # Fallback broader searches
            search_queries.append(f"repo:{Config.GITHUB_REPO} extension:tsx extension:ts")
            
            for query in search_queries:
                if len(relevant_files) >= max_files:
                    break
                    
                print(f"GitHub search query: {query}")
                try:
                    code_results = self.github.search_code(query=query)
                    
                    for idx, result in enumerate(code_results):
                        if len(relevant_files) >= max_files:
                            break
                        
                        # Skip if we've already seen this file
                        if result.path in seen_paths:
                            continue
                            
                        try:
                            print(f"  Fetching file {idx+1}: {result.path}")
                            content = self.repo.get_contents(result.path)
                            
                            # Get larger files now for complete context
                            if content.size < 200000:  # Increased limit to 200KB
                                decoded_content = base64.b64decode(content.content).decode('utf-8')
                                print(f"    File size: {len(decoded_content)} chars")
                                relevant_files.append({
                                    'path': result.path,
                                    'content': decoded_content,  # COMPLETE file content
                                    'url': content.html_url
                                })
                                seen_paths.add(result.path)
                            else:
                                print(f"    Skipping large file: {content.size} bytes")
                        except Exception as e:
                            print(f"  Error getting file {result.path}: {e}")
                            continue
                except Exception as search_error:
                    print(f"  Search query failed: {search_error}")
                    continue
            
        except Exception as e:
            print(f"Error searching repository: {e}")
        
        return relevant_files
    
    def get_file_content(self, file_path: str) -> str:
        """Get content of a specific file from the repository.
        
        Args:
            file_path: Path to the file in the repository
            
        Returns:
            File content as string, or empty string if not found
        """
        try:
            print(f"Fetching specific file: {file_path}")
            file_obj = self.repo.get_contents(file_path)
            
            if file_obj.size < 500000:  # 500KB limit
                content = base64.b64decode(file_obj.content).decode('utf-8')
                print(f"  Fetched {len(content)} characters")
                return content
            else:
                print(f"  File too large: {file_obj.size} bytes")
                return ""
        except Exception as e:
            print(f"  Error fetching file: {e}")
            return ""
    
    def analyze_codebase_context(self, affected_components: List[str]) -> str:
        """Analyze codebase for context around affected components.
        
        Args:
            affected_components: List of affected files/components
            
        Returns:
            Code context string
        """
        context_parts = []
        
        # Handle None case
        if affected_components is None:
            affected_components = []
        
        for component in affected_components[:5]:  # Limit to 5 components
            try:
                # Try to get file content
                if '.' in component:  # Likely a file
                    try:
                        content = self.repo.get_contents(component)
                        if content.size < 50000:
                            file_content = base64.b64decode(content.content).decode('utf-8')
                            context_parts.append(f"=== {component} ===\n{file_content[:1000]}")
                    except:
                        pass
                
                # Search for references
                search_results = self.github.search_code(
                    query=f"repo:{Config.GITHUB_REPO} {component}"
                )
                
                for result in search_results[:2]:
                    context_parts.append(f"Reference in {result.path}")
                    
            except:
                continue
        
        return "\n\n".join(context_parts) if context_parts else "No specific code context found"
