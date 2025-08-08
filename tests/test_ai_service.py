"""
AI Service Tests for Case Management Suite
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from backend.modules.ai_enhanced.enhanced_service import AIService
from backend.core.config import settings


class TestAIService:
    """Test suite for Enhanced AI Service"""
    
    @pytest.fixture
    def ai_service(self):
        """Create AI service instance for testing"""
        return AIService()
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        with patch('backend.modules.ai_enhanced.enhanced_service.AsyncOpenAI') as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client
    
    @pytest.fixture
    def sample_context(self):
        """Sample context for testing"""
        return {
            "client_id": "test_client_123",
            "user_id": "test_user_456",
            "session_id": "test_session_789"
        }
    
    @pytest.mark.asyncio
    async def test_ai_service_initialization(self, ai_service):
        """Test AI service initialization"""
        assert ai_service.client is None
        assert ai_service.function_registry == {}
        assert ai_service.conversation_memory == {}
        assert ai_service._initialized is False
    
    @pytest.mark.asyncio
    async def test_ai_service_initialize(self, ai_service, mock_openai_client):
        """Test AI service initialization with OpenAI client"""
        # Mock settings
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            mock_settings.ai.openai_api_key = "test_key"
            mock_settings.ai.timeout = 30.0
            mock_settings.ai.max_retries = 3
            
            await ai_service.initialize()
            
            assert ai_service._initialized is True
            assert ai_service.client is not None
            assert len(ai_service.function_registry) > 0
    
    @pytest.mark.asyncio
    async def test_function_registry(self, ai_service):
        """Test function registry setup"""
        # Initialize service to register functions
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            mock_settings.ai.openai_api_key = "test_key"
            mock_settings.ai.timeout = 30.0
            mock_settings.ai.max_retries = 3
            
            await ai_service.initialize()
            
            # Check that expected functions are registered
            expected_functions = [
                "create_task", "update_task", "get_client_tasks",
                "prioritize_tasks", "analyze_client_risk", "generate_reminders",
                "search_resources", "create_case_note", "schedule_appointment",
                "get_client_profile", "update_client_status"
            ]
            
            for func_name in expected_functions:
                assert func_name in ai_service.function_registry
                assert callable(ai_service.function_registry[func_name])
    
    @pytest.mark.asyncio
    async def test_generate_response_basic(self, ai_service, mock_openai_client, sample_context):
        """Test basic response generation"""
        # Mock OpenAI response with proper structure - no function call
        mock_message = Mock()
        mock_message.content = "This is a test response"
        mock_message.function_call = None  # No function call
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Mock settings
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            # Create a proper mock settings object
            mock_settings.ai.openai_api_key = "test_key"
            mock_settings.ai.openai_model = "gpt-4"
            mock_settings.ai.openai_temperature = 0.7
            mock_settings.ai.openai_max_tokens = 1000
            
            await ai_service.initialize()
            
            # Mock the function definitions to return proper JSON-serializable data
            with patch.object(ai_service, '_get_function_definitions', return_value=[]):
                # Also mock the client to avoid any JSON serialization issues
                with patch.object(ai_service, 'client', mock_openai_client):
                    response = await ai_service.generate_response(
                        prompt="Test prompt",
                        context=sample_context
                    )
            
            assert response == "This is a test response"
            mock_openai_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_with_conversation_memory(self, ai_service, mock_openai_client):
        """Test response generation with conversation memory"""
        # Mock OpenAI response with proper structure - no function call
        mock_message = Mock()
        mock_message.content = "Response with memory"
        mock_message.function_call = None  # No function call
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Mock settings
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            mock_settings.ai.openai_api_key = "test_key"
            mock_settings.ai.openai_model = "gpt-4"
            mock_settings.ai.openai_temperature = 0.7
            mock_settings.ai.openai_max_tokens = 1000
            
            await ai_service.initialize()
            
            # Add conversation memory
            user_id = "test_user_123"
            ai_service.conversation_memory[user_id] = [
                {"role": "user", "content": "Previous message"},
                {"role": "assistant", "content": "Previous response"}
            ]
            
            context = {"user_id": user_id}
            # Mock the function definitions to return proper JSON-serializable data
            with patch.object(ai_service, '_get_function_definitions', return_value=[]):
                # Also mock the client to avoid any JSON serialization issues
                with patch.object(ai_service, 'client', mock_openai_client):
                    response = await ai_service.generate_response(
                        prompt="New message",
                        context=context
                    )
            
            assert response == "Response with memory"
            # Verify that conversation history was included
            call_args = mock_openai_client.chat.completions.create.call_args
            messages = call_args[1]['messages']
            assert len(messages) >= 4  # system + user + 2 memory messages
    
    @pytest.mark.asyncio
    async def test_analyze_text_sentiment(self, ai_service, mock_openai_client):
        """Test text analysis for sentiment"""
        # Mock OpenAI response with proper structure
        mock_message = Mock()
        mock_message.content = "Positive sentiment with 0.8 confidence"
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Mock settings
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            mock_settings.ai.openai_api_key = "test_key"
            mock_settings.ai.openai_model = "gpt-4"
            mock_settings.ai.openai_temperature = 0.7
            
            await ai_service.initialize()
            
            analysis = await ai_service.analyze_text(
                text="I'm feeling great about my progress!",
                analysis_type="sentiment"
            )
            
            assert isinstance(analysis, dict)
            assert "analysis_type" in analysis
            assert "raw_analysis" in analysis
            assert analysis["analysis_type"] == "sentiment"
    
    @pytest.mark.asyncio
    async def test_function_call(self, ai_service):
        """Test function calling capability"""
        # Mock a function in the registry
        mock_function = AsyncMock(return_value={"status": "success", "task_id": "123"})
        ai_service.function_registry["create_task"] = mock_function
        
        result = await ai_service.function_call(
            function_name="create_task",
            parameters={
                "client_id": "test_client",
                "title": "Test task",
                "description": "Test description"
            }
        )
        
        assert result == {"status": "success", "task_id": "123"}
        mock_function.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_function_call_invalid_function(self, ai_service):
        """Test function call with invalid function name"""
        with pytest.raises(ValueError):
            await ai_service.function_call(
                function_name="invalid_function",
                parameters={}
            )
    
    @pytest.mark.asyncio
    async def test_generate_smart_reminders(self, ai_service, mock_openai_client):
        """Test smart reminder generation"""
        # Mock OpenAI response with proper structure
        mock_message = Mock()
        mock_message.content = """
        Here are some smart reminders:
        1. Follow up on housing application - Due in 3 days
        2. Schedule job interview - Due in 1 week
        3. Complete benefits paperwork - Due in 5 days
        """
        mock_message.function_call = None  # No function call
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Mock settings
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            mock_settings.ai.openai_api_key = "test_key"
            mock_settings.ai.openai_model = "gpt-4"
            mock_settings.ai.openai_temperature = 0.7
            mock_settings.ai.openai_max_tokens = 1000
            
            await ai_service.initialize()
            
            # Mock the function definitions to return proper JSON-serializable data
            with patch.object(ai_service, '_get_function_definitions', return_value=[]):
                # Also mock the client to avoid any JSON serialization issues
                with patch.object(ai_service, 'client', mock_openai_client):
                    reminders = await ai_service.generate_smart_reminders(
                        client_id="test_client_123",
                        context={"client_needs": "housing and employment"}
                    )
            
            assert isinstance(reminders, list)
            assert len(reminders) > 0
    
    @pytest.mark.asyncio
    async def test_build_system_message(self, ai_service, sample_context):
        """Test system message building"""
        system_message = ai_service._build_system_message(sample_context)
        
        assert isinstance(system_message, str)
        assert len(system_message) > 0
        assert "test_client_123" in system_message
    
    @pytest.mark.asyncio
    async def test_get_function_definitions(self, ai_service):
        """Test function definitions generation"""
        # Initialize service to register functions
        with patch('backend.modules.ai_enhanced.enhanced_service.settings') as mock_settings:
            mock_settings.ai.openai_api_key = "test_key"
            await ai_service.initialize()
            
            function_definitions = ai_service._get_function_definitions()
            
            assert isinstance(function_definitions, list)
            assert len(function_definitions) > 0
            
            # Check that each function definition has required fields
            for func_def in function_definitions:
                assert "name" in func_def
                assert "description" in func_def
                assert "parameters" in func_def
    
    @pytest.mark.asyncio
    async def test_handle_function_call(self, ai_service):
        """Test function call handling"""
        # Mock function call
        mock_function_call = Mock()
        mock_function_call.name = "create_task"
        mock_function_call.arguments = '{"client_id": "123", "title": "Test"}'
        
        # Mock function in registry
        mock_function = AsyncMock(return_value={"status": "success"})
        ai_service.function_registry["create_task"] = mock_function
        
        result = await ai_service._handle_function_call(
            function_call=mock_function_call,
            context={"user_id": "test_user"}
        )
        
        assert isinstance(result, dict)
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_parse_reminders_from_text(self, ai_service):
        """Test reminder parsing from text"""
        text = """
        Here are the reminders:
        1. Follow up on housing application - Due in 3 days
        2. Schedule job interview - Due in 1 week
        3. Complete benefits paperwork - Due in 5 days
        """
        
        reminders = ai_service._parse_reminders_from_text(text)
        
        assert isinstance(reminders, list)
        assert len(reminders) >= 3
        
        for reminder in reminders:
            assert "title" in reminder
            assert "due_date_days" in reminder
    
    @pytest.mark.asyncio
    async def test_create_task_function(self, ai_service):
        """Test create_task function"""
        result = await ai_service._create_task(
            client_id="test_client",
            title="Test task",
            description="Test description",
            priority="high",
            category="housing",
            due_date_days=7
        )
        
        assert isinstance(result, dict)
        assert "ai_generated" in result
        assert "client_id" in result
    
    @pytest.mark.asyncio
    async def test_get_client_tasks_function(self, ai_service):
        """Test get_client_tasks function"""
        result = await ai_service._get_client_tasks("test_client")
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_prioritize_tasks_function(self, ai_service):
        """Test prioritize_tasks function"""
        tasks = [
            {"id": "1", "title": "Task 1", "priority": "low"},
            {"id": "2", "title": "Task 2", "priority": "high"},
            {"id": "3", "title": "Task 3", "priority": "medium"}
        ]
        
        result = await ai_service._prioritize_tasks(tasks)
        
        assert isinstance(result, list)
        assert len(result) == len(tasks)
    
    @pytest.mark.asyncio
    async def test_analyze_client_risk_function(self, ai_service):
        """Test analyze_client_risk function"""
        result = await ai_service._analyze_client_risk("test_client")
        
        assert isinstance(result, dict)
        assert "risk_level" in result or "risk_score" in result
    
    @pytest.mark.asyncio
    async def test_search_resources_function(self, ai_service):
        """Test search_resources function"""
        result = await ai_service._search_resources(
            query="housing assistance",
            resource_type="housing",
            location="Los Angeles"
        )
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_create_case_note_function(self, ai_service):
        """Test create_case_note function"""
        result = await ai_service._create_case_note(
            client_id="test_client",
            title="Test note",
            content="Test content",
            note_type="general"
        )
        
        assert isinstance(result, dict)
        assert "client_id" in result
        assert "content" in result
    
    @pytest.mark.asyncio
    async def test_schedule_appointment_function(self, ai_service):
        """Test schedule_appointment function"""
        result = await ai_service._schedule_appointment(
            client_id="test_client",
            title="Test appointment",
            date="2024-01-15",
            time="10:00 AM"
        )
        
        assert isinstance(result, dict)
        assert "client_id" in result
        assert "title" in result
    
    @pytest.mark.asyncio
    async def test_get_client_profile_function(self, ai_service):
        """Test get_client_profile function"""
        result = await ai_service._get_client_profile("test_client")
        
        assert isinstance(result, dict)
        assert "id" in result
    
    @pytest.mark.asyncio
    async def test_update_client_status_function(self, ai_service):
        """Test update_client_status function"""
        result = await ai_service._update_client_status(
            client_id="test_client",
            status="active",
            notes="Client is making progress"
        )
        
        assert isinstance(result, dict)
        assert "client_id" in result
        assert "updated" in result


if __name__ == "__main__":
    pytest.main([__file__]) 